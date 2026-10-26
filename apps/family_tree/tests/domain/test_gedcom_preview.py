import datetime
import io
from pathlib import Path

import pytest

from apps.family_tree.domain.gedcom import read
from apps.family_tree.domain.gedcom_preview import Preview, UnreadableGedcomError, preview, preview_file

TODAY = datetime.date(2026, 10, 25)
# The anonymised PAF export of #32 - see docs/patterns/testing-data.md. A test pins counts, never a name or a date.
PAF_EXPORT = Path(__file__).parent.parent / "data" / "paf_export.ged"
# The anonymised MyHeritage export of #84, the same way.
MYHERITAGE_EXPORT = Path(__file__).parent.parent / "data" / "myheritage_export.ged"


def _preview(text: str) -> Preview:
    return preview(records=read(file=io.BytesIO(text.encode())), today=TODAY)


def test_preview_file_reads_the_paf_export():
    with PAF_EXPORT.open("rb") as file:
        result = preview_file(file=file, today=TODAY)

    assert (result.program, result.charset, result.people, result.families) == ("PAF", "UTF-8", 412, 163)


def test_preview_file_reads_the_myheritage_export():
    with MYHERITAGE_EXPORT.open("rb") as file:
        result = preview_file(file=file, today=TODAY)

    assert (result.program, result.people, result.families, result.photos_url, result.unreadable_dates) == (
        "MYHERITAGE",
        171,
        75,
        39,
        2,
    )


def test_preview_file_refuses_a_file_that_is_not_gedcom():
    with pytest.raises(UnreadableGedcomError, match="keine GEDCOM-Datei"):
        preview_file(file=io.BytesIO(b"0 HEAD\nLiebe Oma,\n0 TRLR\n"), today=TODAY)


def test_preview_counts_people_families_and_sources():
    result = _preview(
        "0 HEAD\n0 @I1@ INDI\n1 NAME Lena /Huber/\n0 @I2@ INDI\n1 NAME Josef /Huber/\n"
        "0 @F1@ FAM\n1 HUSB @I2@\n1 WIFE @I1@\n0 @S1@ SOUR\n1 TITL Taufbuch\n0 TRLR\n"
    )

    assert (result.people, result.families, result.sources) == (2, 1, 1)


def test_preview_names_the_program_and_the_character_set_from_the_header():
    result = _preview("0 HEAD\n1 SOUR MyHeritage\n2 NAME MyHeritage Family Tree Builder\n1 CHAR UTF-8\n0 TRLR\n")

    assert (result.program, result.charset) == ("MyHeritage", "UTF-8")


def test_preview_leaves_program_and_character_set_empty_without_a_header():
    result = _preview("0 @I1@ INDI\n1 NAME Lena /Huber/\n")

    assert (result.program, result.charset) == ("", "")


def test_preview_tells_the_photos_apart_by_their_path():
    result = _preview(
        "0 HEAD\n1 FILE huber.ged\n"
        "0 @I1@ INDI\n1 OBJE\n2 FILE C:\\Fotos\\lena.jpg\n1 OBJE\n2 FILE https://example.org/lena.jpg\n"
        "0 @O1@ OBJE\n1 FILE fotos/josef.jpg\n0 @O2@ OBJE\n1 FILE D:/Scans/taufe.jpg\n0 TRLR\n"
    )

    assert (result.photos_windows, result.photos_url, result.photos_other, result.photos) == (2, 1, 1, 4)


def test_preview_names_each_tag_of_the_program_once():
    result = _preview("0 @I1@ INDI\n1 _UID 4F2A\n1 NAME Lena /Huber/\n2 _MARNM Gruber\n0 @I2@ INDI\n1 _UID 9B1C\n")

    assert result.own_tags == ("_MARNM", "_UID")


def test_preview_warns_about_people_without_a_name():
    result = _preview("0 @I1@ INDI\n1 NAME Lena /Huber/\n0 @I2@ INDI\n1 SEX M\n0 @I3@ INDI\n1 NAME //\n")

    assert (result.unnamed, result.warnings) == (2, 2)


def test_preview_warns_about_dates_in_the_future():
    result = _preview(
        "0 @I1@ INDI\n1 BIRT\n2 DATE 2031\n1 DEAT\n2 DATE 12 MAR 1989\n0 @F1@ FAM\n1 MARR\n2 DATE ABT 2050\n"
    )

    assert result.future_dates == 2


def test_preview_counts_the_dates_it_cannot_read_but_not_when_a_record_was_changed():
    result = _preview("0 @I1@ INDI\n1 BIRT\n2 DATE Frühjahr 1939\n1 CHAN\n2 DATE gestern\n")

    assert result.unreadable_dates == 1


def test_preview_reads_a_day_written_the_german_way_as_the_import_does():
    result = _preview("0 @I1@ INDI\n1 BIRT\n2 DATE 07.03.1962\n1 DEAT\n2 DATE 07.03.2062\n")

    assert (result.unreadable_dates, result.future_dates) == (0, 1)


def test_preview_warns_about_people_with_an_address_or_an_email_but_not_about_the_submitter():
    result = _preview(
        "0 @U1@ SUBM\n1 ADDR Hauptplatz 1\n"
        "0 @I1@ INDI\n1 RESI\n2 ADDR Hauptplatz 1\n0 @I2@ INDI\n1 EMAIL lena@example.org\n0 @I3@ INDI\n"
    )

    assert result.with_contact == 2


def test_preview_of_a_plain_file_has_nothing_to_warn_about():
    result = _preview("0 HEAD\n0 @I1@ INDI\n1 NAME Lena /Huber/\n1 BIRT\n2 DATE 1989\n0 TRLR\n")

    assert result.warnings == 0
