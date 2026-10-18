"""
The uncertain date of a fact, structured after GEDCOM as decided in #5 - see docs/patterns/evidence.md.

Pure functions: no database, no Django. The model stores the fields of "UncertainDate"; this module turns
GEDCOM date strings into it and back, and derives the date a list sorts by.
"""

import datetime
import re
from dataclasses import dataclass
from enum import StrEnum


class DateKind(StrEnum):
    EXACT = "exact"
    ABOUT = "about"  # GEDCOM ABT, and EST and CAL, which Zweigerl does not tell apart
    BEFORE = "before"  # BEF
    AFTER = "after"  # AFT
    BETWEEN = "between"  # BET ... AND ...


class Precision(StrEnum):
    DAY = "day"
    MONTH = "month"
    YEAR = "year"


@dataclass(frozen=True, kw_only=True)
class UncertainDate:
    """
    "date_1" and "date_2" are real dates; a month or a year is stored as its first day, and "precision" says
    how much of it is known. "date_2" exists for "between" only.
    """

    kind: DateKind
    date_1: datetime.date
    precision: Precision
    date_2: datetime.date | None = None


MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")

PREFIXES = {
    "ABT": DateKind.ABOUT,
    "EST": DateKind.ABOUT,
    "CAL": DateKind.ABOUT,
    "BEF": DateKind.BEFORE,
    "AFT": DateKind.AFTER,
}
GEDCOM_PREFIX = {DateKind.ABOUT: "ABT", DateKind.BEFORE: "BEF", DateKind.AFTER: "AFT"}

SIMPLE_DATE = re.compile(r"^(?:(?:(\d{1,2}) )?([A-Z]{3}) )?(\d{3,4})$")


def from_gedcom(*, text: str) -> UncertainDate:
    """
    Reads a GEDCOM 5.5.1 date: "1931", "APR 1989", "12 MAR 1989", "ABT 1931", "BEF 1850", "AFT 1850",
    "BET 1820 AND 1825". Raises ValueError for anything else - a date phrase, FROM/TO periods, another
    calendar, a range whose ends are not equally precise - which the importer keeps raw instead (#22).
    """
    parts = text.strip().upper().split()
    if not parts:
        raise ValueError("Kein Datum angegeben.")

    if parts[0] == "BET" and "AND" in parts:
        and_at = parts.index("AND")
        date_1, precision = _simple_date(text=" ".join(parts[1:and_at]))
        date_2, precision_2 = _simple_date(text=" ".join(parts[and_at + 1 :]))
        # One precision for both ends is what Zweigerl stores; a mixed range is kept raw by the importer
        # rather than written back with a day nobody gave or without one somebody did.
        if precision_2 != precision:
            raise ValueError(f"„{text}“: beide Daten müssen gleich genau sein.")
        if date_2 < date_1:
            raise ValueError(f"„{text}“: das zweite Datum liegt vor dem ersten.")
        return UncertainDate(kind=DateKind.BETWEEN, date_1=date_1, date_2=date_2, precision=precision)

    kind = PREFIXES.get(parts[0])
    rest = parts[1:] if kind else parts
    date_1, precision = _simple_date(text=" ".join(rest))
    return UncertainDate(kind=kind or DateKind.EXACT, date_1=date_1, precision=precision)


def to_gedcom(*, date: UncertainDate) -> str:
    """
    The GEDCOM 5.5.1 form of a structured date, the inverse of "from_gedcom".
    """
    first = _as_simple_date(date=date.date_1, precision=date.precision)
    if date.kind == DateKind.BETWEEN:
        second = _as_simple_date(date=date.date_2, precision=date.precision)
        return f"BET {first} AND {second}"
    if date.kind == DateKind.EXACT:
        return first
    return f"{GEDCOM_PREFIX[date.kind]} {first}"


def sort_date(*, date: UncertainDate) -> datetime.date:
    """
    The date a list sorts and filters by: the date itself, and for "between" the middle of the range, so
    "between 1820 and 1830" sorts beside 1825 rather than beside 1820. The range runs to the end of its
    last month or year: "1820 to 1825" is the whole of 1825 too.
    """
    if date.kind == DateKind.BETWEEN:
        end = _last_day(date=date.date_2, precision=date.precision)
        return date.date_1 + (end - date.date_1) / 2
    return date.date_1


def _last_day(*, date: datetime.date, precision: Precision) -> datetime.date:
    if precision == Precision.YEAR:
        return datetime.date(date.year, 12, 31)
    if precision == Precision.MONTH:
        next_month = datetime.date(date.year + date.month // 12, date.month % 12 + 1, 1)
        return next_month - datetime.timedelta(days=1)
    return date


def _simple_date(*, text: str) -> tuple[datetime.date, Precision]:
    match = SIMPLE_DATE.match(text)
    if match is None:
        raise ValueError(f"„{text}“ ist kein Datum, das Zweigerl lesen kann.")
    day, month, year = match.groups()
    if month is not None and month not in MONTHS:
        raise ValueError(f"„{month}“ ist kein Monat.")
    try:
        if day is not None:
            return datetime.date(int(year), MONTHS.index(month) + 1, int(day)), Precision.DAY
        if month is not None:
            return datetime.date(int(year), MONTHS.index(month) + 1, 1), Precision.MONTH
        return datetime.date(int(year), 1, 1), Precision.YEAR
    except ValueError as error:
        raise ValueError(f"„{text}“ ist kein gültiges Datum.") from error


def _as_simple_date(*, date: datetime.date, precision: Precision) -> str:
    if precision == Precision.DAY:
        return f"{date.day} {MONTHS[date.month - 1]} {date.year}"
    if precision == Precision.MONTH:
        return f"{MONTHS[date.month - 1]} {date.year}"
    return str(date.year)


YEAR_PREFIX = {DateKind.ABOUT: "um", DateKind.BEFORE: "vor", DateKind.AFTER: "nach"}


def year_text(*, date: UncertainDate) -> str:
    """
    The year of a date as a list shows it, in German: "1931", "um 1931", "vor 1850", "nach 1850", and
    "1820/1825" for a range. The day and the month are left to the person's card.
    """
    if date.kind == DateKind.BETWEEN:
        return f"{date.date_1.year}/{date.date_2.year}"
    prefix = YEAR_PREFIX.get(date.kind)
    return f"{prefix} {date.date_1.year}" if prefix else str(date.date_1.year)


GERMAN_MONTHS = (
    "Jänner",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
)


def date_text(*, date: UncertainDate) -> str:
    """
    A date as the person's card shows it, in German and only as precise as it is known: "12. März 1989",
    "März 1989", "um 1931", "vor April 1850", "zwischen 1820 und 1825".
    """
    first = _german_date(date=date.date_1, precision=date.precision)
    if date.kind == DateKind.BETWEEN:
        return f"zwischen {first} und {_german_date(date=date.date_2, precision=date.precision)}"
    prefix = YEAR_PREFIX.get(date.kind)
    return f"{prefix} {first}" if prefix else first


def _german_date(*, date: datetime.date, precision: Precision) -> str:
    if precision == Precision.DAY:
        return f"{date.day}. {GERMAN_MONTHS[date.month - 1]} {date.year}"
    if precision == Precision.MONTH:
        return f"{GERMAN_MONTHS[date.month - 1]} {date.year}"
    return str(date.year)


def lifespan(*, birth: UncertainDate | None, death: UncertainDate | None, deceased: bool) -> str:
    """
    The Lebensdaten beside a name: "1931 – 2009", "1958 –" for somebody alive or not known to be dead,
    "1931 – ?" for somebody dead whose death date nobody knows, "? – 2009" without a birth, and "—" when
    nothing is known at all.
    """
    if birth is None and death is None:
        return "—"
    born = year_text(date=birth) if birth else "?"
    if death:
        return f"{born} – {year_text(date=death)}"
    return f"{born} – ?" if deceased else f"{born} –"


EXIF_DATE = re.compile(r"^(\d{4}):(\d{2}):(\d{2})")


def from_exif(*, text: str) -> UncertainDate | None:
    """
    The date a camera wrote into a photo, "2009:07:14 16:02:11", as an exact day - or None for anything a
    camera writes when it does not know, such as "0000:00:00 00:00:00" (#16).
    """
    match = EXIF_DATE.match(text.strip())
    if match is None:
        return None
    try:
        day = datetime.date(*(int(part) for part in match.groups()))
    except ValueError:
        return None
    return UncertainDate(kind=DateKind.EXACT, date_1=day, precision=Precision.DAY)


@dataclass(frozen=True, kw_only=True)
class DateParts:
    """
    A date as the short form for a photo (#16) asks for it: day, month and year as typed, and whether it is
    only roughly right.
    """

    day: str = ""
    month: str = ""
    year: str = ""
    about: bool = False


def from_parts(*, parts: DateParts) -> UncertainDate | None:
    """
    Reads the day, month and year of the form, each optional from the left: "1950", "7 1950", "14 7 1950".
    Nothing at all is no date. Raises ValueError with a German message for a day without a month, a month
    without a year, or numbers that are no date.
    """
    day, month, year = (part.strip() for part in (parts.day, parts.month, parts.year))
    if not (day or month or year):
        return None
    if not year or (day and not month):
        raise ValueError("Ein Datum braucht das Jahr, und ein Tag braucht den Monat.")
    if not all(part.isdecimal() for part in (day, month, year) if part):
        raise ValueError("Tag, Monat und Jahr sind Zahlen, etwa 14, 7 und 1950.")
    try:
        date_1 = datetime.date(int(year), int(month or 1), int(day or 1))
    except ValueError as error:
        raise ValueError(f"{'.'.join(part for part in (day, month, year) if part)} ist kein gültiges Datum.") from error

    precision = Precision.DAY if day else Precision.MONTH if month else Precision.YEAR
    return UncertainDate(kind=DateKind.ABOUT if parts.about else DateKind.EXACT, date_1=date_1, precision=precision)


def to_parts(*, date: UncertainDate | None) -> DateParts:
    """
    The inverse of "from_parts", to fill the form in again. A date before, after or between is shown by its
    first day; the form cannot say more than "ungefähr".
    """
    if date is None:
        return DateParts()
    return DateParts(
        day=str(date.date_1.day) if date.precision == Precision.DAY else "",
        month=str(date.date_1.month) if date.precision != Precision.YEAR else "",
        year=str(date.date_1.year),
        about=date.kind == DateKind.ABOUT,
    )
