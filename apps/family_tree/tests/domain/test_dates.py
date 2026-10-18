import datetime

import pytest

from apps.family_tree.domain.dates import (
    DateKind,
    Precision,
    UncertainDate,
    date_text,
    from_gedcom,
    lifespan,
    sort_date,
    to_gedcom,
    year_text,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1931", UncertainDate(kind=DateKind.EXACT, date_1=datetime.date(1931, 1, 1), precision=Precision.YEAR)),
        (
            "APR 1989",
            UncertainDate(kind=DateKind.EXACT, date_1=datetime.date(1989, 4, 1), precision=Precision.MONTH),
        ),
        (
            "12 MAR 1989",
            UncertainDate(kind=DateKind.EXACT, date_1=datetime.date(1989, 3, 12), precision=Precision.DAY),
        ),
        (
            "ABT 1931",
            UncertainDate(kind=DateKind.ABOUT, date_1=datetime.date(1931, 1, 1), precision=Precision.YEAR),
        ),
        (
            "est 1931",
            UncertainDate(kind=DateKind.ABOUT, date_1=datetime.date(1931, 1, 1), precision=Precision.YEAR),
        ),
        (
            "BEF 1850",
            UncertainDate(kind=DateKind.BEFORE, date_1=datetime.date(1850, 1, 1), precision=Precision.YEAR),
        ),
        (
            "AFT 1850",
            UncertainDate(kind=DateKind.AFTER, date_1=datetime.date(1850, 1, 1), precision=Precision.YEAR),
        ),
        (
            "BET 1820 AND 1825",
            UncertainDate(
                kind=DateKind.BETWEEN,
                date_1=datetime.date(1820, 1, 1),
                date_2=datetime.date(1825, 1, 1),
                precision=Precision.YEAR,
            ),
        ),
    ],
)
def test_from_gedcom_reads_every_form(text, expected):
    assert from_gedcom(text=text) == expected


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "Kein Datum angegeben"),
        ("um 1931", "kein Datum, das Zweigerl lesen kann"),
        ("12 FOO 1931", "kein Monat"),
        ("31 FEB 1931", "kein gültiges Datum"),
        ("BET 1825 AND 1820", "das zweite Datum liegt vor dem ersten"),
        ("BET 1820 AND", "kein Datum, das Zweigerl lesen kann"),
        ("BET 12 MAR 1820 AND 1825", "beide Daten müssen gleich genau sein"),
    ],
)
def test_from_gedcom_refuses_what_it_cannot_read(text, message):
    with pytest.raises(ValueError, match=message):
        from_gedcom(text=text)


@pytest.mark.parametrize(
    "text", ["1931", "APR 1989", "12 MAR 1989", "ABT 1931", "BEF 1850", "AFT 1850", "BET 1820 AND 1825"]
)
def test_to_gedcom_writes_what_from_gedcom_reads(text):
    assert to_gedcom(date=from_gedcom(text=text)) == text


def test_sort_date_is_the_date_itself():
    date = UncertainDate(kind=DateKind.BEFORE, date_1=datetime.date(1850, 1, 1), precision=Precision.YEAR)

    assert sort_date(date=date) == datetime.date(1850, 1, 1)


def test_sort_date_of_a_range_is_its_middle():
    date = UncertainDate(
        kind=DateKind.BETWEEN,
        date_1=datetime.date(1820, 3, 1),
        date_2=datetime.date(1820, 3, 31),
        precision=Precision.DAY,
    )

    assert sort_date(date=date) == datetime.date(1820, 3, 16)


def test_sort_date_of_a_range_of_years_runs_to_the_end_of_the_last():
    date = from_gedcom(text="BET 1820 AND 1821")

    assert sort_date(date=date) == datetime.date(1820, 12, 31)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("BET JAN 1820 AND FEB 1820", datetime.date(1820, 1, 30)),
        ("BET NOV 1820 AND DEC 1820", datetime.date(1820, 12, 1)),
    ],
)
def test_sort_date_of_a_range_of_months_runs_to_the_end_of_the_last(text, expected):
    assert sort_date(date=from_gedcom(text=text)) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12 MAR 1931", "1931"),
        ("ABT 1931", "um 1931"),
        ("BEF 1850", "vor 1850"),
        ("AFT 1850", "nach 1850"),
        ("BET 1820 AND 1825", "1820/1825"),
    ],
)
def test_year_text_says_the_year_in_german(text, expected):
    assert year_text(date=from_gedcom(text=text)) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12 MAR 1989", "12. März 1989"),
        ("JAN 1989", "Jänner 1989"),
        ("ABT 1931", "um 1931"),
        ("BEF APR 1850", "vor April 1850"),
        ("AFT 1850", "nach 1850"),
        ("BET 1820 AND 1825", "zwischen 1820 und 1825"),
    ],
)
def test_date_text_says_the_date_in_german_as_precisely_as_it_is_known(text, expected):
    assert date_text(date=from_gedcom(text=text)) == expected


def test_lifespan_with_birth_and_death():
    result = lifespan(birth=from_gedcom(text="1931"), death=from_gedcom(text="ABT 2009"), deceased=True)

    assert result == "1931 – um 2009"


def test_lifespan_of_somebody_not_known_to_be_dead_stays_open():
    assert lifespan(birth=from_gedcom(text="1958"), death=None, deceased=False) == "1958 –"


def test_lifespan_of_somebody_dead_without_a_death_date_asks_for_it():
    assert lifespan(birth=from_gedcom(text="1931"), death=None, deceased=True) == "1931 – ?"


def test_lifespan_without_a_birth_date():
    assert lifespan(birth=None, death=from_gedcom(text="2009"), deceased=True) == "? – 2009"


def test_lifespan_when_nothing_is_known():
    assert lifespan(birth=None, death=None, deceased=True) == "—"
