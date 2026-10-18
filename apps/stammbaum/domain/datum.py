"""
The uncertain date of an Angabe, structured after GEDCOM as decided in #5 - see docs/patterns/belege.md.

Pure functions: no database, no Django. The model stores the fields of "UnscharfesDatum"; this module turns
GEDCOM date strings into it and back, and derives the date a list sorts by.
"""

import datetime
import re
from dataclasses import dataclass
from enum import StrEnum


class DatumArt(StrEnum):
    GENAU = "genau"
    UNGEFAEHR = "ungefaehr"  # GEDCOM ABT, and EST and CAL, which Zweigerl does not tell apart
    VOR = "vor"  # BEF
    NACH = "nach"  # AFT
    ZWISCHEN = "zwischen"  # BET ... AND ...


class Genauigkeit(StrEnum):
    TAG = "tag"
    MONAT = "monat"
    JAHR = "jahr"


@dataclass(frozen=True, kw_only=True)
class UnscharfesDatum:
    """
    "datum_1" and "datum_2" are real dates; a month or a year is stored as its first day, and "genauigkeit"
    says how much of it is known. "datum_2" exists for "zwischen" only.
    """

    art: DatumArt
    datum_1: datetime.date
    genauigkeit: Genauigkeit
    datum_2: datetime.date | None = None


MONATE = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")

PRAEFIXE = {
    "ABT": DatumArt.UNGEFAEHR,
    "EST": DatumArt.UNGEFAEHR,
    "CAL": DatumArt.UNGEFAEHR,
    "BEF": DatumArt.VOR,
    "AFT": DatumArt.NACH,
}
GEDCOM_PRAEFIX = {DatumArt.UNGEFAEHR: "ABT", DatumArt.VOR: "BEF", DatumArt.NACH: "AFT"}

EINFACHES_DATUM = re.compile(r"^(?:(?:(\d{1,2}) )?([A-Z]{3}) )?(\d{3,4})$")


def aus_gedcom(*, text: str) -> UnscharfesDatum:
    """
    Reads a GEDCOM 5.5.1 date: "1931", "APR 1989", "12 MAR 1989", "ABT 1931", "BEF 1850", "AFT 1850",
    "BET 1820 AND 1825". Raises ValueError for anything else - a date phrase, FROM/TO periods, another
    calendar - which the importer keeps raw instead (#22).
    """
    teile = text.strip().upper().split()
    if not teile:
        raise ValueError("Kein Datum angegeben.")

    if teile[0] == "BET" and "AND" in teile:
        und = teile.index("AND")
        datum_1, genauigkeit = _einfaches_datum(text=" ".join(teile[1:und]))
        datum_2, genauigkeit_2 = _einfaches_datum(text=" ".join(teile[und + 1 :]))
        # One precision for both ends is what Zweigerl stores; a mixed range is kept raw by the importer
        # rather than written back with a day nobody gave or without one somebody did.
        if genauigkeit_2 != genauigkeit:
            raise ValueError(f"„{text}“: beide Daten müssen gleich genau sein.")
        if datum_2 < datum_1:
            raise ValueError(f"„{text}“: das zweite Datum liegt vor dem ersten.")
        return UnscharfesDatum(art=DatumArt.ZWISCHEN, datum_1=datum_1, datum_2=datum_2, genauigkeit=genauigkeit)

    art = PRAEFIXE.get(teile[0])
    rest = teile[1:] if art else teile
    datum_1, genauigkeit = _einfaches_datum(text=" ".join(rest))
    return UnscharfesDatum(art=art or DatumArt.GENAU, datum_1=datum_1, genauigkeit=genauigkeit)


def als_gedcom(*, datum: UnscharfesDatum) -> str:
    """
    The GEDCOM 5.5.1 form of a structured date, the inverse of "aus_gedcom".
    """
    erstes = _als_einfaches_datum(datum=datum.datum_1, genauigkeit=datum.genauigkeit)
    if datum.art == DatumArt.ZWISCHEN:
        zweites = _als_einfaches_datum(datum=datum.datum_2, genauigkeit=datum.genauigkeit)
        return f"BET {erstes} AND {zweites}"
    if datum.art == DatumArt.GENAU:
        return erstes
    return f"{GEDCOM_PRAEFIX[datum.art]} {erstes}"


def sortierdatum(*, datum: UnscharfesDatum) -> datetime.date:
    """
    The date a list sorts and filters by: the date itself, and for "zwischen" the middle of the range, so
    "between 1820 and 1830" sorts beside 1825 rather than beside 1820. The range runs to the end of its
    last month or year: "1820 to 1825" is the whole of 1825 too.
    """
    if datum.art == DatumArt.ZWISCHEN:
        ende = _letzter_tag(datum=datum.datum_2, genauigkeit=datum.genauigkeit)
        return datum.datum_1 + (ende - datum.datum_1) / 2
    return datum.datum_1


def _letzter_tag(*, datum: datetime.date, genauigkeit: Genauigkeit) -> datetime.date:
    if genauigkeit == Genauigkeit.JAHR:
        return datetime.date(datum.year, 12, 31)
    if genauigkeit == Genauigkeit.MONAT:
        naechster = datetime.date(datum.year + datum.month // 12, datum.month % 12 + 1, 1)
        return naechster - datetime.timedelta(days=1)
    return datum


def _einfaches_datum(*, text: str) -> tuple[datetime.date, Genauigkeit]:
    treffer = EINFACHES_DATUM.match(text)
    if treffer is None:
        raise ValueError(f"„{text}“ ist kein Datum, das Zweigerl lesen kann.")
    tag, monat, jahr = treffer.groups()
    if monat is not None and monat not in MONATE:
        raise ValueError(f"„{monat}“ ist kein Monat.")
    try:
        if tag is not None:
            return datetime.date(int(jahr), MONATE.index(monat) + 1, int(tag)), Genauigkeit.TAG
        if monat is not None:
            return datetime.date(int(jahr), MONATE.index(monat) + 1, 1), Genauigkeit.MONAT
        return datetime.date(int(jahr), 1, 1), Genauigkeit.JAHR
    except ValueError as fehler:
        raise ValueError(f"„{text}“ ist kein gültiges Datum.") from fehler


def _als_einfaches_datum(*, datum: datetime.date, genauigkeit: Genauigkeit) -> str:
    if genauigkeit == Genauigkeit.TAG:
        return f"{datum.day} {MONATE[datum.month - 1]} {datum.year}"
    if genauigkeit == Genauigkeit.MONAT:
        return f"{MONATE[datum.month - 1]} {datum.year}"
    return str(datum.year)
