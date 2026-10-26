"""The anonymised MyHeritage export of #84 keeps what the import has to cope with beside a PAF export.

The file is written by `scripts/anonymise_gedcom.py` from a real export that never enters the repository, so
these tests check its structure only - never an invented name or date, which change with every run.
"""

import itertools
import re
from pathlib import Path

import pytest

MYHERITAGE_EXPORT = Path(__file__).parent / "myheritage_export.ged"
# A value may end in a stray LF inside the CRLF file - one of the forms the file is kept for.
LINE = re.compile(r"(?P<level>\d+) (?:(?P<xref>@[^@]+@) )?(?P<tag>\S+)(?: (?P<value>.*))?", re.DOTALL)


@pytest.fixture(scope="module")
def raw() -> bytes:
    return MYHERITAGE_EXPORT.read_bytes()


@pytest.fixture(scope="module")
def rows(raw) -> list[str]:
    # MyHeritage ends the last line without a line break.
    return raw.decode("utf-8").removeprefix("﻿").split("\r\n")


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


def test_myheritage_export_starts_with_a_bom_and_ends_its_lines_with_crlf_but_the_last(raw):
    assert (raw.startswith(b"\xef\xbb\xbf"), raw.endswith(b"\r\n"), raw.count(b"\r\n") > 1000) == (True, False, True)


def test_myheritage_export_parses_as_gedcom(rows):
    levels = [int(match["level"]) for match in map(LINE.fullmatch, rows) if match]

    assert (
        len(levels) == len(rows),
        all(level <= previous + 1 for previous, level in itertools.pairwise(levels)),
        rows[0],
        rows[-1],
    ) == (True, True, "0 HEAD", "0 TRLR")


def test_myheritage_export_declares_myheritage_gedcom_551_and_utf8(paths):
    assert {"HEAD/SOUR MYHERITAGE", "HEAD/GEDC/VERS 5.5.1", "HEAD/CHAR UTF-8", "HEAD/LANG German"} <= set(paths)


def test_myheritage_export_has_a_stray_line_break_inside_a_value(raw):
    assert re.search(rb"[^\r]\n\r\n", raw) is not None


@pytest.mark.parametrize(
    ("form", "pattern"),
    [
        ("day month year", r".*/DATE \d{1,2} [A-Z]{3} \d{4}"),
        ("the German way", r".*/DATE \d{1,2}\.\d{1,2}\.\d{4}"),
        ("a period's end", r"INDI/RESI/DATE TO .+"),
        ("the year only", r".*/DATE \d{4}"),
    ],
)
def test_myheritage_export_has_date_form(paths, form, pattern):
    assert any(re.fullmatch(pattern, line) for line in paths), form


@pytest.mark.parametrize(
    ("form", "pattern"),
    [
        ("a death that says only that it happened", r"INDI/DEAT Y"),
        ("an age at death", r"INDI/DEAT/AGE \d+"),
        ("an age at death as a range", r"INDI/DEAT/AGE \d+-\d+"),
        ("an age at death about a range", r"INDI/DEAT/AGE About \d+-\d+"),
        ("a baptism", r"INDI/BAPM"),
        ("an address", r"INDI/RESI/ADDR/CITY .+"),
        ("an email", r"INDI/RESI/EMAIL .+@@.+"),
        ("an occupation with a place", r"INDI/OCCU/PLAC .+"),
        ("a call name", r"INDI/NAME/NICK .+"),
        ("a married name", r"INDI/NAME/_MARNM .+"),
        ("a source found by MyHeritage", r"SOUR/_TYPE Discovery"),
        ("a citation on the person with a page", r"INDI/SOUR/PAGE .+"),
        ("its quality", r"INDI/SOUR/QUAY 3"),
        ("the event it is for", r"INDI/SOUR/EVEN .+"),
        ("its wording", r"INDI/SOUR/DATA/TEXT .+"),
        ("its date", r"INDI/SOUR/DATA/DATE .+"),
        ("a wedding licence", r"FAM/MARL"),
        ("an event of a family with a type", r"FAM/EVEN/TYPE .+"),
        ("a photo behind a URL", r"INDI/OBJE/FILE https://[^/]+\.mhcache\.com/.+\.jpg"),
        ("a portrait", r"INDI/OBJE/_PRIM Y"),
        ("a cutout of a group photo", r"INDI/OBJE/_CUTOUT Y"),
        ("its position", r"INDI/OBJE/_POSITION .+"),
        ("a record number", r"INDI/RIN MH:.+"),
        ("a change date", r"INDI/_UPD .+"),
    ],
)
def test_myheritage_export_has_record_form(paths, form, pattern):
    assert any(re.fullmatch(pattern, line) for line in paths), form
