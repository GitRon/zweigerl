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
    The Lebensdaten beside a name, in the signs of genealogy: "* 1931 † 2009", "* 1958" for somebody alive or not
    known to be dead, "* 1931 †" for somebody dead whose death date nobody knows, "† 2009" without a birth, "†"
    for somebody dead and nothing else, and nothing at all when nothing is known. No dash: an open "1958 –" reads
    as a death date somebody forgot.
    """
    parts = []
    if birth:
        parts.append(f"* {year_text(date=birth)}")
    if death:
        parts.append(f"† {year_text(date=death)}")
    elif deceased:
        parts.append("†")
    return " ".join(parts)


GERMAN_PREFIXES = {
    "um": DateKind.ABOUT,
    "ca.": DateKind.ABOUT,
    "ca": DateKind.ABOUT,
    "circa": DateKind.ABOUT,
    "etwa": DateKind.ABOUT,
    "vor": DateKind.BEFORE,
    "nach": DateKind.AFTER,
}
# Every month the card writes, the two spellings north of the border, and the short forms people type - with or
# without their dot, which "_german_month" takes off.
GERMAN_MONTH_NUMBERS = {
    **{name.lower(): number for number, name in enumerate(GERMAN_MONTHS, start=1)},
    "januar": 1,
    "feber": 2,
    "jan": 1,
    "jän": 1,
    "feb": 2,
    "mär": 3,
    "mrz": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "okt": 10,
    "nov": 11,
    "dez": 12,
}
RANGE_WORDS = {"zwischen": "und", "von": "bis"}

ISO_DAY = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
DOTTED_DAY = re.compile(r"^(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{3,4})$")
NAMED_DAY = re.compile(r"^(\d{1,2})\.?\s*([^\W\d_]+\.?)\s+(\d{3,4})$")
NAMED_MONTH = re.compile(r"^([^\W\d_]+\.?)\s+(\d{3,4})$")
DOTTED_MONTH = re.compile(r"^(\d{1,2})\.\s*(\d{3,4})$")
YEAR = re.compile(r"^(\d{3,4})$")
# "1820/1825" as "year_text" writes a range, and "1820-1825" or "1820–1825" as people type one.
SHORT_RANGE = re.compile(r"^(.+?)\s*[/–-]\s*(.+)$")
TWO_DIGIT_YEAR = re.compile(r"^(.*[.\s])(\d{2})$")
UNSURE = re.compile(r"^(.*?)\s*(?:\(\?\)|\?)$")
SEASON = re.compile(r"^(?:frühjahr|frühling|sommer|herbst|winter|anfang|mitte|ende)\s+(\d{3,4})$", re.IGNORECASE)


def from_german(*, text: str) -> UncertainDate:
    """
    Reads a date as a person types it into the form for a fact (#14): everything "date_text" and "year_text" write
    - "1931", "März 1989", "12. März 1989", "zwischen 1820 und 1825", "1820/1825" - and "3.1989", "12.3.1989",
    "12.März 1989", short months such as "Sept." or "Mär", "1820-1825", "von 1820 bis 1825" and "1989-03-12". A
    date may follow "um" (also "ca.", "circa", "etwa"), "vor" or "nach".

    Raises ValueError with a German message for anything else, and for a range whose ends are not equally precise
    or run backwards - the same as "from_gedcom". What it will not guess - a two-digit year, a question mark, a
    season, two dates joined by "oder" - it explains, with the nearest form it does read.
    """
    typed = " ".join(text.split())
    if not typed:
        raise ValueError("Kein Datum angegeben.")
    _refuse_guesses(typed=typed)

    words = typed.split()
    lowered = [word.lower() for word in words]
    closing = RANGE_WORDS.get(lowered[0])
    if closing in lowered:
        at = lowered.index(closing)
        return _german_range(typed=typed, first=" ".join(words[1:at]), second=" ".join(words[at + 1 :]))
    if match := ISO_DAY.match(typed):
        date_1 = _checked_date(text=typed, year=int(match[1]), month=int(match[2]), day=int(match[3]))
        return UncertainDate(kind=DateKind.EXACT, date_1=date_1, precision=Precision.DAY)
    if match := SHORT_RANGE.match(typed):
        return _german_range(typed=typed, first=match[1], second=match[2])

    kind = GERMAN_PREFIXES.get(lowered[0])
    rest = words[1:] if kind else words
    date_1, precision = _german_simple_date(text=" ".join(rest))
    return UncertainDate(kind=kind or DateKind.EXACT, date_1=date_1, precision=precision)


def _refuse_guesses(*, typed: str) -> None:
    # "(?)" means "maybe wrong", not "roughly", and a season or "oder" has no structured form - so rather than
    # store a date nobody meant, the message names the nearest one Zweigerl does read.
    if (match := UNSURE.match(typed)) and match[1]:
        unsure = match[1]
        first = unsure.split()[0].lower()
        nearest = unsure if first in GERMAN_PREFIXES or first in RANGE_WORDS else f"um {unsure}"
        raise ValueError(f"„{typed}“: Unsicher? Dann etwa „{nearest}“.")
    if match := SEASON.match(typed):
        raise ValueError(f"„{typed}“ kann Zweigerl nicht lesen. Am nächsten kommt „um {match[1]}“.")
    words = typed.split()
    lowered = [word.lower() for word in words]
    if "oder" in lowered:
        at = lowered.index("oder")
        nearest = _between(first=" ".join(words[:at]), second=" ".join(words[at + 1 :]))
        raise ValueError(f"„{typed}“: Für zwei mögliche Daten schreib „{nearest}“.")


def _between(*, first: str, second: str) -> str:
    try:
        earlier_second = _german_simple_date(text=second)[0] < _german_simple_date(text=first)[0]
    except ValueError:
        return "zwischen 1820 und 1825"
    return f"zwischen {second} und {first}" if earlier_second else f"zwischen {first} und {second}"


def _german_range(*, typed: str, first: str, second: str) -> UncertainDate:
    date_1, precision = _german_simple_date(text=first)
    date_2, precision_2 = _german_simple_date(text=second)
    if precision_2 != precision:
        raise ValueError(f"„{typed}“: beide Daten müssen gleich genau sein, etwa „zwischen 1820 und 1825“.")
    if date_2 < date_1:
        raise ValueError(f"„{typed}“: das zweite Datum liegt vor dem ersten.")
    return UncertainDate(kind=DateKind.BETWEEN, date_1=date_1, date_2=date_2, precision=precision)


def _german_simple_date(*, text: str) -> tuple[datetime.date, Precision]:
    year, month, day, precision = _german_parts(text=text)
    return _checked_date(text=text, year=year, month=month, day=day), precision


def _checked_date(*, text: str, year: int, month: int, day: int) -> datetime.date:
    try:
        return datetime.date(year, month, day)
    except ValueError as error:
        raise ValueError(f"„{text}“ ist kein gültiges Datum.") from error


def _german_parts(*, text: str) -> tuple[int, int, int, Precision]:
    # Year, month and day; a month is its first day and a year its 1 January, as the model stores them.
    if match := DOTTED_DAY.match(text):
        return int(match[3]), int(match[2]), int(match[1]), Precision.DAY
    if match := NAMED_DAY.match(text):
        return int(match[3]), _german_month(name=match[2]), int(match[1]), Precision.DAY
    if match := NAMED_MONTH.match(text):
        return int(match[2]), _german_month(name=match[1]), 1, Precision.MONTH
    if match := DOTTED_MONTH.match(text):
        return int(match[2]), int(match[1]), 1, Precision.MONTH
    if match := YEAR.match(text):
        return int(match[1]), 1, 1, Precision.YEAR
    if match := TWO_DIGIT_YEAR.match(text):
        # In a family tree 1862 is as likely as 1962, so a silent century would be a wrong date nobody notices.
        before, year = match[1], match[2]
        raise ValueError(f"„{text}“ hat ein zweistelliges Jahr. Meinst du {before}18{year} oder {before}19{year}?")
    raise ValueError(f"„{text}“ ist kein Datum, das Zweigerl lesen kann - {_examples(text=text)}.")


def _examples(*, text: str) -> str:
    # Examples in the form that was typed: a month by its name, by its number, or neither.
    if re.search(r"[^\W\d_]", text):
        return "etwa März 1989, 12. März 1989 oder um 1931"
    if "." in text:
        return "etwa 12.3.1989, 3.1989 oder 1931"
    return "etwa 1931, um 1931 oder 12. März 1989"


def _german_month(*, name: str) -> int:
    number = GERMAN_MONTH_NUMBERS.get(name.lower().removesuffix("."))
    if number is None:
        raise ValueError(f"„{name}“ ist kein Monat - etwa März, Mär. oder 3.")
    return number


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
