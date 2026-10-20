"""The anonymised PAF export of #32 keeps what the import (#22) has to cope with.

The file is written by `scripts/anonymise_paf.py` from a real export that never enters the repository, so
these tests check its structure only - never an invented name or date, which change with every run.
"""

import itertools
import re
import unicodedata
from pathlib import Path

import pytest

PAF_EXPORT = Path(__file__).parent / "paf_export.ged"
MONTH = r"(?i:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)"
LINE = re.compile(r"(?P<level>\d+) (?:(?P<xref>@[^@]+@) )?(?P<tag>\S+)(?: (?P<value>.*))?")


@pytest.fixture(scope="module")
def raw() -> bytes:
    return PAF_EXPORT.read_bytes()


@pytest.fixture(scope="module")
def text(raw) -> str:
    return raw.decode("utf-8")


@pytest.fixture(scope="module")
def rows(text) -> list[str]:
    return text.removeprefix("﻿").split("\r\n")[:-1]


@pytest.fixture(scope="module")
def levels(rows) -> list[int]:
    """The level of every line that parses."""
    return [int(match["level"]) for match in map(LINE.fullmatch, rows) if match]


@pytest.fixture(scope="module")
def paths(rows) -> list[str]:
    """Every line as `INDI/BIRT/DATE <value>`, the tags from its record down to itself."""
    stack = []
    lines = []
    for row in rows:
        match = LINE.fullmatch(row)
        stack = [*stack[: int(match["level"])], match["tag"]]
        lines.append(f"{'/'.join(stack)} {match['value'] or ''}".rstrip())
    return lines


def test_paf_export_starts_with_a_bom(raw):
    assert raw.startswith(b"\xef\xbb\xbf") is True


def test_paf_export_ends_every_line_with_crlf(raw):
    assert (raw.endswith(b"\r\n"), raw.count(b"\n") == raw.count(b"\r\n")) == (True, True)


def test_paf_export_parses_as_gedcom(rows, levels):
    assert (
        len(levels) == len(rows),
        all(level <= previous + 1 for previous, level in itertools.pairwise(levels)),
        rows[0],
        rows[-1],
    ) == (True, True, "0 HEAD", "0 TRLR")


def test_paf_export_declares_paf_and_utf8(paths):
    assert {"HEAD/SOUR PAF", "HEAD/SOUR/VERS 5.2.18.0", "HEAD/CHAR UTF-8", "HEAD/LANG German"} <= set(paths)


def test_paf_export_is_nfc(text):
    assert text == unicodedata.normalize("NFC", text)


@pytest.mark.parametrize(
    ("form", "pattern"),
    [
        ("umlaut", r"[äöüÄÖÜ]"),
        ("sharp s", r"ß"),
        ("letter beyond Latin-1", r"[^\x00-\xff﻿]"),
        ("typographic quotation mark", r"[«»„“”‚‘’]"),  # noqa: RUF001
        ("dagger", r"†"),
    ],
)
def test_paf_export_keeps_non_ascii(text, form, pattern):
    assert re.search(pattern, text) is not None, form


@pytest.mark.parametrize(
    ("form", "pattern"),
    [
        ("German month name", r".*/DATE .*\b(Januar|Februar|März|Mär|April|Mai|Juni|Juli|August|Okt|Oktober|Dez)\b.*"),
        ("two dates joined by 'oder'", r".*/DATE .+ oder .+"),
        ("a question mark", r".*/DATE .*\(\?\)"),
        ("a season", r".*/DATE (Frühjahr|Frühling|Sommer|Herbst|Winter) \d{4}"),
        ("text without a digit", r".*/DATE \D+"),
        ("ABT", r".*/DATE ABT .+"),
        ("BEF", r".*/DATE BEF .+"),
        ("AFT", r".*/DATE AFT .+"),
        ("the year only", r".*/DATE \d{4}"),
        ("month and year", rf".*/DATE {MONTH} \d{{4}}"),
        ("day and month without a year", rf".*/DATE \d{{1,2}} {MONTH}"),
        ("the date of a change", r"INDI/CHAN/DATE \d{1,2} [A-Za-z]{3} \d{4}"),
    ],
)
def test_paf_export_has_date_form(paths, form, pattern):
    assert any(re.fullmatch(pattern, line) for line in paths), form


@pytest.mark.parametrize(
    ("form", "pattern"),
    [
        ("an empty surname", r"INDI/NAME [^/]+ //"),
        ("an unknown surname", r"INDI/NAME [^/]+ /\?/"),
        ("the surname only", r"INDI/NAME /[^/?]+/"),
        ("a double surname", r"INDI/NAME [^/]* /[^/]+-[^/]+/"),
        ("a comma in the given names", r"INDI/NAME [^/]*,[^/]* /.*/"),
        ("a call name", r"INDI/NAME/NICK .+"),
        ("a title", r"INDI/NAME/NPFX .+"),
        ("a married name", r"INDI/NAME/_MARNM .+"),
        ("another name", r"INDI/NAME/_AKA .+"),
    ],
)
def test_paf_export_has_name_form(paths, form, pattern):
    assert any(re.fullmatch(pattern, line) for line in paths), form


@pytest.mark.parametrize(
    ("form", "line"),
    [
        ("a divorce on the person", "INDI/DIV"),
        ("a first communion", "INDI/FCOM"),
        ("a divorce marked Y", "FAM/DIV Y"),
        ("a cause of death", "INDI/DEAT/CAUS"),
        ("a description", "INDI/DSCR"),
        ("a citation with a page", "INDI/BIRT/SOUR/PAGE"),
        ("a portrait", "INDI/OBJE/_PRIM Y"),
        ("a scrapbook flag", "INDI/OBJE/_SCBK Y"),
        ("a slide show flag", "INDI/OBJE/_SSHOW Y"),
        ("a picture type", "INDI/OBJE/_TYPE PHOTO"),
        ("a picture below a citation", "INDI/OCCU/SOUR/OBJE/FILE"),
        ("a picture below a source", "SOUR/OBJE/FILE"),
    ],
)
def test_paf_export_has_record_form(paths, form, line):
    assert any(path == line or path.startswith(f"{line} ") for path in paths), form


def test_paf_export_has_a_marriage_without_a_date(raw):
    assert re.search(rb"\r\n1 MARR ?\r\n(?!2 DATE)", raw) is not None


def test_paf_export_has_a_family_with_one_parent(raw):
    families = re.split(rb"\r\n0 ", raw)

    assert any(
        b" FAM\r\n" in family and (b"\r\n1 HUSB " in family) != (b"\r\n1 WIFE " in family) for family in families
    )


def test_paf_export_splits_a_note_mid_word(text):
    assert re.search(r"[^\W\d_]\r\n\d CONC [^\W\d_]", text) is not None


def test_paf_export_keeps_windows_paths_with_their_extensions(paths):
    assert any(re.fullmatch(r".*OBJE/FILE [^\\]+\\[^\\]+\.(jpg|png)", line) for line in paths)
