import datetime

import pytest

from apps.family_tree.domain.dates import (
    DateKind,
    Precision,
    UncertainDate,
    date_text,
    from_exif,
    from_gedcom,
    from_german,
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

    assert result == "* 1931 † um 2009"


def test_lifespan_of_somebody_not_known_to_be_dead_has_no_dash():
    assert lifespan(birth=from_gedcom(text="1958"), death=None, deceased=False) == "* 1958"


def test_lifespan_of_somebody_dead_without_a_death_date_shows_the_cross():
    assert lifespan(birth=from_gedcom(text="ABT 1931"), death=None, deceased=True) == "* um 1931 †"


def test_lifespan_without_a_birth_date():
    assert lifespan(birth=None, death=from_gedcom(text="2009"), deceased=True) == "† 2009"


def test_lifespan_of_somebody_dead_with_nothing_else_known():
    assert lifespan(birth=None, death=None, deceased=True) == "†"


def test_lifespan_when_nothing_is_known():
    assert lifespan(birth=None, death=None, deceased=False) == ""


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1931", "1931"),
        ("März 1989", "MAR 1989"),
        ("3.1989", "MAR 1989"),
        ("12. März 1989", "12 MAR 1989"),
        ("12 märz 1989", "12 MAR 1989"),
        ("12.3.1989", "12 MAR 1989"),
        ("12. 03. 1989", "12 MAR 1989"),
        ("Januar 1989", "JAN 1989"),
        ("Feber 1989", "FEB 1989"),
        ("um 1931", "ABT 1931"),
        ("ca. 1931", "ABT 1931"),
        ("etwa 1931", "ABT 1931"),
        ("vor April 1850", "BEF APR 1850"),
        ("nach 1850", "AFT 1850"),
        ("  zwischen 1820  und 1825 ", "BET 1820 AND 1825"),
        ("12. Sept. 1989", "12 SEP 1989"),
        ("Mär 1989", "MAR 1989"),
        ("Okt. 1950", "OCT 1950"),
        ("Dez 1938", "DEC 1938"),
        ("um Jän. 1900", "ABT JAN 1900"),
        ("12.März 1989", "12 MAR 1989"),
        ("1820/1825", "BET 1820 AND 1825"),
        ("1820-1825", "BET 1820 AND 1825"),
        ("1820 – 1825", "BET 1820 AND 1825"),
        ("Von 1820 bis 1825", "BET 1820 AND 1825"),
        ("1989-03-12", "12 MAR 1989"),
    ],
)
def test_from_german_reads_what_a_person_types(text, expected):
    assert from_german(text=text) == from_gedcom(text=expected)


@pytest.mark.parametrize(
    "text", ["12 MAR 1989", "JAN 1989", "ABT 1931", "BEF APR 1850", "AFT 1850", "BET 1820 AND 1825"]
)
def test_from_german_reads_what_date_text_writes(text):
    date = from_gedcom(text=text)

    assert from_german(text=date_text(date=date)) == date


@pytest.mark.parametrize("text", ["1931", "ABT 1931", "BEF 1850", "AFT 1850", "BET 1820 AND 1825"])
def test_from_german_reads_what_year_text_writes(text):
    date = from_gedcom(text=text)

    assert from_german(text=year_text(date=date)) == date


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "Kein Datum angegeben"),
        ("irgendwann", "kein Datum, das Zweigerl lesen kann - etwa März 1989"),
        ("12..1989", "kein Datum, das Zweigerl lesen kann - etwa 12.3.1989"),
        ("12 34 5", "kein Datum, das Zweigerl lesen kann - etwa 1931"),
        ("Brumaire 1799", "„Brumaire“ ist kein Monat - etwa März"),
        ("31.2.1989", "kein gültiges Datum"),
        ("1989-02-30", "„1989-02-30“ ist kein gültiges Datum"),
        ("zwischen März 1820 und 1825", "beide Daten müssen gleich genau sein"),
        ("zwischen 1825 und 1820", "das zweite Datum liegt vor dem ersten"),
        ("1825/1820", "das zweite Datum liegt vor dem ersten"),
    ],
)
def test_from_german_refuses_what_it_cannot_read(text, message):
    with pytest.raises(ValueError, match=message):
        from_german(text=text)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("07.03.62", r"„07.03.62“ hat ein zweistelliges Jahr. Meinst du 07.03.1862 oder 07.03.1962\?"),
        ("März 62", r"Meinst du März 1862 oder März 1962\?"),
        ("1926 (?)", r"„1926 \(\?\)“: Unsicher\? Dann etwa „um 1926“"),
        ("1926?", r"Dann etwa „um 1926“"),
        ("um 1926?", r"Dann etwa „um 1926“"),
        ("Frühjahr 1965", "„Frühjahr 1965“ kann Zweigerl nicht lesen. Am nächsten kommt „um 1965“"),
        ("Anfang 1965", "Am nächsten kommt „um 1965“"),
        ("1927 oder 1926", "„1927 oder 1926“: Für zwei mögliche Daten schreib „zwischen 1926 und 1927“"),
        ("1926 oder 1927", "schreib „zwischen 1926 und 1927“"),
        ("Ostern oder Pfingsten", "schreib „zwischen 1820 und 1825“"),
    ],
)
def test_from_german_explains_what_it_will_not_guess(text, message):
    with pytest.raises(ValueError, match=message):
        from_german(text=text)


def test_from_exif_reads_the_day_the_camera_wrote():
    assert from_exif(text="2009:07:14 16:02:11") == UncertainDate(
        kind=DateKind.EXACT, date_1=datetime.date(2009, 7, 14), precision=Precision.DAY
    )


@pytest.mark.parametrize("text", ["0000:00:00 00:00:00", "2009:02:30 10:00:00", "gestern", ""])
def test_from_exif_ignores_what_is_no_date(text):
    assert from_exif(text=text) is None
