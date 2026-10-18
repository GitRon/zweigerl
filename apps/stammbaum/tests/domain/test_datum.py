import datetime

import pytest

from apps.stammbaum.domain.datum import DatumArt, Genauigkeit, UnscharfesDatum, als_gedcom, aus_gedcom, sortierdatum


@pytest.mark.parametrize(
    ("text", "erwartet"),
    [
        ("1931", UnscharfesDatum(art=DatumArt.GENAU, datum_1=datetime.date(1931, 1, 1), genauigkeit=Genauigkeit.JAHR)),
        (
            "APR 1989",
            UnscharfesDatum(art=DatumArt.GENAU, datum_1=datetime.date(1989, 4, 1), genauigkeit=Genauigkeit.MONAT),
        ),
        (
            "12 MAR 1989",
            UnscharfesDatum(art=DatumArt.GENAU, datum_1=datetime.date(1989, 3, 12), genauigkeit=Genauigkeit.TAG),
        ),
        (
            "ABT 1931",
            UnscharfesDatum(art=DatumArt.UNGEFAEHR, datum_1=datetime.date(1931, 1, 1), genauigkeit=Genauigkeit.JAHR),
        ),
        (
            "est 1931",
            UnscharfesDatum(art=DatumArt.UNGEFAEHR, datum_1=datetime.date(1931, 1, 1), genauigkeit=Genauigkeit.JAHR),
        ),
        (
            "BEF 1850",
            UnscharfesDatum(art=DatumArt.VOR, datum_1=datetime.date(1850, 1, 1), genauigkeit=Genauigkeit.JAHR),
        ),
        (
            "AFT 1850",
            UnscharfesDatum(art=DatumArt.NACH, datum_1=datetime.date(1850, 1, 1), genauigkeit=Genauigkeit.JAHR),
        ),
        (
            "BET 1820 AND 1825",
            UnscharfesDatum(
                art=DatumArt.ZWISCHEN,
                datum_1=datetime.date(1820, 1, 1),
                datum_2=datetime.date(1825, 1, 1),
                genauigkeit=Genauigkeit.JAHR,
            ),
        ),
    ],
)
def test_aus_gedcom_reads_every_form(text, erwartet):
    assert aus_gedcom(text=text) == erwartet


@pytest.mark.parametrize(
    ("text", "meldung"),
    [
        ("", "Kein Datum angegeben"),
        ("um 1931", "kein Datum, das Zweigerl lesen kann"),
        ("12 FOO 1931", "kein Monat"),
        ("31 FEB 1931", "kein gültiges Datum"),
        ("BET 1825 AND 1820", "das zweite Datum liegt vor dem ersten"),
        ("BET 1820 AND", "kein Datum, das Zweigerl lesen kann"),
    ],
)
def test_aus_gedcom_refuses_what_it_cannot_read(text, meldung):
    with pytest.raises(ValueError, match=meldung):
        aus_gedcom(text=text)


@pytest.mark.parametrize(
    "text", ["1931", "APR 1989", "12 MAR 1989", "ABT 1931", "BEF 1850", "AFT 1850", "BET 1820 AND 1825"]
)
def test_als_gedcom_writes_what_aus_gedcom_reads(text):
    assert als_gedcom(datum=aus_gedcom(text=text)) == text


def test_sortierdatum_is_the_date_itself():
    datum = UnscharfesDatum(art=DatumArt.VOR, datum_1=datetime.date(1850, 1, 1), genauigkeit=Genauigkeit.JAHR)

    assert sortierdatum(datum=datum) == datetime.date(1850, 1, 1)


def test_sortierdatum_of_a_range_is_its_middle():
    datum = UnscharfesDatum(
        art=DatumArt.ZWISCHEN,
        datum_1=datetime.date(1820, 3, 1),
        datum_2=datetime.date(1820, 3, 31),
        genauigkeit=Genauigkeit.TAG,
    )

    assert sortierdatum(datum=datum) == datetime.date(1820, 3, 16)
