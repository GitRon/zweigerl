import random
import re
import runpy
import sys
from unittest import mock

import pytest

from scripts import anonymise_gedcom
from scripts.anonymise_gedcom import (
    FEMALE_NAMES,
    MALE_NAMES,
    SURNAMES,
    AnonymiseError,
    Anonymiser,
    Line,
    Unit,
    anonymise,
    char_class,
    forbidden_words,
    joined_text,
    main,
    month_index,
    month_name,
    parse,
    refuse_leaks,
    rule_for,
    split_text,
    units,
)

# A tree as PAF writes it, invented throughout.
EXPORT = (
    "\ufeff0 HEAD\r\n"
    "1 SOUR PAF\r\n"
    "2 NAME Personal Ancestral File\r\n"
    "1 DATE 12 MAR 1989\r\n"
    "1 FILE huber.ged\r\n"
    "1 CHAR UTF-8\r\n"
    "0 @I1@ INDI\r\n"
    "1 NAME Josef Alois /Huber/\r\n"
    "2 GIVN Josef Alois\r\n"
    "2 SURN Huber\r\n"
    "1 SEX M\r\n"
    "1 BIRT\r\n"
    "2 DATE 9 Mär 1931 oder 9.3.1931\r\n"
    "2 PLAC Gmunden, Oberösterreich\r\n"
    "1 NOTE Josef war Schmied in Gmun\r\n"
    "2 CONC den.\r\n"
    "1 _UID 4F2A93\r\n"
    "0 @I2@ INDI\r\n"
    "1 NAME Maria /Huber/\r\n"
    "2 _MARNM Huber\r\n"
    "1 SEX F\r\n"
    "0 TRLR\r\n"
)


@pytest.fixture
def anonymiser() -> Anonymiser:
    return Anonymiser(rng=random.Random(0), forbidden=set(), offset_days=-3660)


def test_line_render_writes_xref_and_value():
    line = Line(level=0, xref="@I1@", tag="INDI", value=None)

    assert line.render() == "0 @I1@ INDI"


def test_line_render_keeps_an_empty_value():
    line = Line(level=1, xref=None, tag="BURI", value="")

    assert line.render() == "1 BURI "


def test_parse_renders_the_text_it_read():
    assert parse(text=EXPORT).render() == EXPORT


def test_parse_keeps_lf_without_bom_and_without_a_last_line_break():
    text = "0 HEAD\n0 TRLR"

    assert parse(text=text).render() == text


def test_parse_keeps_a_stray_line_break_inside_a_value():
    text = "0 @I1@ INDI\r\n1 BIRT\r\n2 PLAC Gmunden \n\r\n0 TRLR\r\n"

    document = parse(text=text)

    assert (document.lines[2].value, document.render()) == ("Gmunden \n", text)


def test_parse_refuses_a_line_that_is_no_gedcom():
    with pytest.raises(AnonymiseError, match=r"Line 2 is not a GEDCOM line."):
        parse(text="0 HEAD\r\nHuber\r\n")


@pytest.mark.parametrize(
    ("text", "expected"),
    [("Huber", "ascii"), ("Gößl", "latin1"), ("Dvořák", "beyond")],
)
def test_char_class(text, expected):
    assert char_class(text=text) == expected


@pytest.mark.parametrize(
    ("path", "value", "expected"),
    [
        (["INDI", "BIRT"], None, "keep"),
        (["INDI", "FAMS"], "@F1@", "keep"),
        (["HEAD", "DATE"], "12 MAR 1989", "date"),
        (["HEAD", "FILE"], "huber.ged", "file"),
        (["HEAD", "NOTE"], "Stammbaum Huber", "text"),
        (["HEAD", "CHAR"], "UTF-8", "keep"),
        (["HEAD", "SOUR", "NAME"], "Personal Ancestral File", "keep"),
        (["HEAD", "SOUR", "CORP", "ADDR"], "Salt Lake City", "keep"),
        (["SUBM", "NAME"], "Josef Huber", "text"),
        (["INDI", "NAME"], "Josef /Huber/", "name"),
        (["INDI", "NAME", "SURN"], "Huber", "surname"),
        (["INDI", "BIRT", "PLAC"], "Gmunden", "place"),
        (["INDI", "NOTE"], "Schmied", "text"),
        (["INDI", "SEX"], "M", "keep"),
        (["FAM", "DIV"], "Y", "keep"),
        (["INDI", "_UID"], "4F2A93", "uid"),
        (["INDI", "RIN"], "MH:I500001", "uid"),
        (["INDI", "OBJE", "_PHOTO_RIN"], "MH:P500001", "uid"),
        (["INDI", "OBJE", "_PARENTRIN"], "MH:PA500001", "uid"),
        (["HEAD", "_PROJECT_GUID"], "4F2A93", "uid"),
        (["HEAD", "_EXPORTED_FROM_SITE_ID"], "123456", "uid"),
        (["SOUR", "_MEDI"], "123456-1", "uid"),
        (["INDI", "_UPD"], "12 MAR 1989 10:11:12 GMT -0500", "date"),
        (["INDI", "DEAT", "AGE"], "About 45-50", "age"),
        (["INDI", "OBJE", "_FILESIZE"], "72219", "text"),
        (["INDI", "OBJE", "_POSITION"], "12 34 56 78", "text"),
        (["INDI", "SOUR", "QUAY"], "3", "keep"),
        (["INDI", "SOUR", "DATA", "TEXT"], "Bestätigt", "text"),
    ],
)
def test_rule_for(path, value, expected):
    assert rule_for(path=path, value=value) == expected


def test_rule_for_refuses_a_value_it_has_no_rule_for():
    with pytest.raises(AnonymiseError, match=r"No rule for a value of INDI/_WOHNORT."):
        rule_for(path=["INDI", "_WOHNORT"], value="Gmunden")


def test_units_join_a_note_with_its_continuations():
    lines = parse(text="0 @I1@ INDI\n1 NOTE Schmied\n2 CONC in\n2 CONT Gmunden\n1 SEX M\n").lines

    assert list(units(lines=lines)) == [
        Unit(rule="keep", indexes=[0], sex="M"),
        Unit(rule="text", indexes=[1, 2, 3], sex="M"),
        Unit(rule="keep", indexes=[4], sex="M"),
    ]


def test_units_stop_at_a_continuation_of_another_level():
    lines = parse(text="0 @I1@ INDI\n1 NOTE Schmied\n1 CONC in\n").lines

    with pytest.raises(AnonymiseError, match=r"No rule for a value of INDI/CONC."):
        list(units(lines=lines))


def test_units_carry_a_late_continuation_on_as_its_line_was():
    lines = parse(text="0 @I1@ INDI\n1 NOTE Schmied\n2 SOUR @S1@\n2 CONT in Gmunden\n2 CONT\n").lines

    assert list(units(lines=lines)) == [
        Unit(rule="keep", indexes=[0], sex=""),
        Unit(rule="text", indexes=[1], sex=""),
        Unit(rule="keep", indexes=[2], sex=""),
        Unit(rule="text", indexes=[3], sex=""),
        Unit(rule="keep", indexes=[4], sex=""),
    ]


def test_units_refuse_a_continuation_of_a_name():
    lines = parse(text="0 @I1@ INDI\n1 NAME Josef /Huber/\n2 CONC er\n").lines

    with pytest.raises(AnonymiseError, match=r"No rule for a value of INDI/NAME/CONC."):
        list(units(lines=lines))


def test_joined_text_breaks_the_line_at_cont_and_joins_at_conc():
    lines = parse(text="1 NOTE Schmied in Gmun\n2 CONC den\n2 CONT\n2 CONT seit 1931\n").lines

    assert joined_text(lines=lines, indexes=[0, 1, 2, 3]) == "Schmied in Gmunden\n\nseit 1931"


def test_split_text_cuts_at_the_same_places():
    lines = parse(text="1 NOTE Schmied in Gmun\n2 CONC den\n2 CONT\n2 CONT seit 1931\n").lines

    split_text(lines=lines, indexes=[0, 1, 2, 3], text="Abcdefg hi Jklmnop\n\nqrst 2468")

    assert lines == parse(text="1 NOTE Abcdefg hi Jklm\n2 CONC nop\n2 CONT\n2 CONT qrst 2468\n").lines


def test_split_text_takes_a_lone_continuation_from_the_start():
    lines = parse(text="2 CONT Gmunden\n").lines

    split_text(lines=lines, indexes=[0], text="Abcdefg")

    assert lines[0].value == "Abcdefg"


def test_forbidden_words_holds_names_places_text_and_paths_but_not_what_stays():
    document = parse(
        text=(
            "0 HEAD\n1 SOUR PAF\n1 DATE 12 MAR 1989\n0 @I1@ INDI\n1 NAME Jo /Ui/\n1 BIRT\n2 PLAC Au\n"
            "1 NOTE Schmied in Wien\n1 OBJE\n2 FILE Fotos\\Taufe.jpg\n2 FORM jpg\n1 DEAT\n2 DATE Sommer 1931\n"
            "2 CAUS Lungenentzündung\n"
        )
    )

    assert forbidden_words(document=document) == {"jo", "ui", "au", "schmied", "wien", "fotos", "taufe",
                                                  "lungenentzündung"}  # fmt: skip


@pytest.mark.parametrize(
    ("index", "tag"),
    [
        (3, "DATE"),
        (4, "FILE"),
        (7, "NAME"),
        (8, "GIVN"),
        (9, "SURN"),
        (12, "DATE"),
        (13, "PLAC"),
        (14, "NOTE"),
        (15, "CONC"),
        (16, "_UID"),
        (18, "NAME"),
        (19, "_MARNM"),
    ],
)
def test_anonymiser_anonymise_replaces_the_value(anonymiser, index, tag):
    document = parse(text=EXPORT)
    original = parse(text=EXPORT).lines[index]

    anonymiser.anonymise(document=document)

    assert (document.lines[index].tag, document.lines[index].value != original.value) == (tag, True)


def test_anonymiser_anonymise_keeps_what_says_nothing_about_a_person(anonymiser):
    document = parse(text=EXPORT)

    anonymiser.anonymise(document=document)

    lines = document.lines
    assert (lines[1].value, lines[2].value, lines[5].value, lines[10].value, lines[11].value, lines[20].value) == (
        "PAF",
        "Personal Ancestral File",
        "UTF-8",
        "M",
        None,
        "F",
    )


def test_anonymiser_anonymise_keeps_the_names_of_a_family_consistent(anonymiser):
    document = parse(text=EXPORT)

    anonymiser.anonymise(document=document)

    josef, alois, huber = document.lines[7].value.replace("/", "").split()
    assert (document.lines[8].value, document.lines[9].value, document.lines[19].value) == (
        f"{josef} {alois}",
        huber,
        huber,
    )


def test_anonymiser_anonymise_cuts_a_note_where_it_was_cut(anonymiser):
    document = parse(text=EXPORT)

    anonymiser.anonymise(document=document)

    assert (len(document.lines[14].value), len(document.lines[15].value)) == (25, 4)


def test_anonymiser_remembered_invents_once(anonymiser):
    first = anonymiser.remembered(key=("word", "Huber"), invent=lambda: "Gruber")

    assert (first, anonymiser.remembered(key=("word", "Huber"), invent=lambda: "Moser")) == ("Gruber", "Gruber")


def test_anonymiser_allowed_refuses_a_forbidden_word():
    anonymiser = Anonymiser(rng=random.Random(0), forbidden={"huber"}, offset_days=-3660)

    assert (anonymiser.allowed(candidate="Leitgeb"), anonymiser.allowed(candidate="Anna Huber")) == (True, False)


def test_anonymiser_choose_skips_forbidden_names():
    anonymiser = Anonymiser(rng=random.Random(0), forbidden={"agathe"}, offset_days=-3660)

    assert anonymiser.choose(candidates=["Agathe", "Berta"], original="Anna") == "Berta"


def test_anonymiser_choose_takes_an_unused_name_first(anonymiser):
    anonymiser.choose(candidates=["Agathe", "Berta"], original="Anna")

    assert anonymiser.choose(candidates=["Agathe", "Berta"], original="Maria") == "Agathe"


def test_anonymiser_choose_reuses_a_name_once_all_are_taken(anonymiser):
    anonymiser.choose(candidates=["Agathe"], original="Anna")

    assert anonymiser.choose(candidates=["Agathe"], original="Maria") == "Agathe"


def test_anonymiser_choose_keeps_capitals(anonymiser):
    assert anonymiser.choose(candidates=["Berta"], original="HUBER") == "BERTA"


def test_anonymiser_choose_keeps_a_single_capital_as_a_name(anonymiser):
    assert anonymiser.choose(candidates=["Berta"], original="A") == "Berta"


def test_anonymiser_choose_scrambles_when_every_name_is_forbidden():
    anonymiser = Anonymiser(rng=random.Random(0), forbidden={"berta"}, offset_days=-3660)

    invented = anonymiser.choose(candidates=["Berta"], original="Anna")

    assert (len(invented), invented[0].isupper(), invented[1:].islower()) == (4, True, True)


@pytest.mark.parametrize(
    ("char", "alphabet"),
    [
        ("7", "0123456789"),
        ("k", anonymise_gedcom.ASCII_LETTERS),
        ("K", anonymise_gedcom.ASCII_LETTERS.upper()),
        ("ö", anonymise_gedcom.LATIN1_LETTERS),
        ("Ž", anonymise_gedcom.BEYOND_LATIN1_LETTERS.upper()),
    ],
)
def test_anonymiser_scramble_char_keeps_the_kind_of_character(anonymiser, char, alphabet):
    assert anonymiser.scramble_char(char=char) in alphabet


@pytest.mark.parametrize("char", ["-", "ß", "†", "„"])
def test_anonymiser_scramble_char_keeps_what_is_no_letter_and_sharp_s(anonymiser, char):
    assert anonymiser.scramble_char(char=char) == char


def test_anonymiser_scramble_gives_up_when_every_word_is_forbidden():
    anonymiser = Anonymiser(rng=random.Random(0), forbidden={"ss"}, offset_days=-3660)

    with pytest.raises(AnonymiseError, match=r"No replacement found for a word of 1 characters."):
        anonymiser.scramble(word="ß")


def test_anonymiser_word_is_consistent(anonymiser):
    first = anonymiser.word(word="Schmied")

    assert (len(first), anonymiser.word(word="Schmied")) == (7, first)


def test_anonymiser_text_keeps_punctuation_and_spaces(anonymiser):
    invented = anonymiser.text(value="„Pepi“, † 1931!")

    assert (invented[0], invented[5:10], invented[14]) == ("„", "“, † ", "!")


@pytest.mark.parametrize(("sex", "pool"), [("F", FEMALE_NAMES["ascii"]), ("M", MALE_NAMES["ascii"])])
def test_anonymiser_given_takes_a_name_of_the_sex(anonymiser, sex, pool):
    assert anonymiser.given(value="Anna", sex=sex) in pool


def test_anonymiser_given_takes_either_pool_without_a_sex(anonymiser):
    assert anonymiser.given(value="Kim", sex="") in FEMALE_NAMES["ascii"] + MALE_NAMES["ascii"]


def test_anonymiser_given_keeps_the_kind_of_letters(anonymiser):
    assert anonymiser.given(value="Jiří", sex="M") in MALE_NAMES["beyond"]


def test_anonymiser_given_keeps_commas_and_brackets(anonymiser):
    invented = anonymiser.given(value="Anna, Maria (Mitzi)", sex="F")

    assert (invented.count(","), invented.count("("), invented.endswith(")")) == (1, 1, True)


def test_anonymiser_surname_maps_each_part_of_a_double_name(anonymiser):
    first, second = anonymiser.surname(value="Huber-Gößl").split("-")

    assert (first in SURNAMES["ascii"], second in SURNAMES["latin1"]) == (True, True)


@pytest.mark.parametrize("surname", ["//", "/?/"])
def test_anonymiser_name_keeps_an_empty_or_unknown_surname(anonymiser, surname):
    assert anonymiser.name(value=f"Josef {surname}", sex="M").endswith(f" {surname}") is True


def test_anonymiser_name_maps_given_and_surname_like_their_own_tags(anonymiser):
    name = anonymiser.name(value="Josef /Huber/ jun", sex="M")

    assert name == (
        f"{anonymiser.given(value='Josef', sex='M')} /{anonymiser.surname(value='Huber')}/ "
        f"{anonymiser.given(value='jun', sex='M')}"
    )


def test_anonymiser_name_without_slashes_is_given_names(anonymiser):
    assert anonymiser.name(value="Pepi", sex="M") == anonymiser.given(value="Pepi", sex="M")


def test_anonymiser_invent_place_keeps_letters_beyond_latin1(anonymiser):
    assert anonymiser.invent_place(part="Plzeň") in anonymise_gedcom.BEYOND_LATIN1_PLACES


def test_anonymiser_invent_place_builds_a_name_with_umlauts(anonymiser):
    assert char_class(text=anonymiser.invent_place(part="Wörgl")) == "latin1"


def test_anonymiser_place_keeps_the_parts_and_their_spaces(anonymiser):
    invented = anonymiser.place(value="Gmunden, , Oberösterreich, Gmunden")

    first, empty, second, again = invented.split(",")
    assert (empty, second.startswith(" "), again == f" {first}") == (" ", True, True)


def test_anonymiser_place_gives_a_part_of_digits_other_digits(anonymiser):
    _city, district = anonymiser.place(value="Wien, 1931.").split(",")

    assert (district[0], district[-1], district[1:5].isdigit(), district[1:5] != "1931") == (" ", ".", True, True)


def test_anonymiser_file_keeps_drive_separators_and_extension(anonymiser):
    invented = anonymiser.file(value="C:\\Fotos\\Taufe Josef_1931.jpg")

    assert (invented[:3], invented[8], invented[14], invented[20], invented[-4:]) == ("C:\\", "\\", " ", "_", ".jpg")


def test_anonymiser_file_without_drive_and_extension(anonymiser):
    assert len(anonymiser.file(value="Fotos\\Taufe")) == 11


def test_anonymiser_file_keeps_the_scheme_and_host_of_a_url(anonymiser):
    url = "https://sites-cf.example.com/Huber/Josef_1931.jpg"

    invented = anonymiser.file(value=url)

    assert (invented[:29], invented[-4:], len(invented), "Huber" in invented) == (url[:29], ".jpg", len(url), False)


def test_forbidden_words_leave_out_the_host_of_a_url():
    document = parse(text="0 @I1@ INDI\n1 OBJE\n2 FILE https://sites.example.com/Huber.jpg\n")

    assert forbidden_words(document=document) == {"huber"}


def test_anonymiser_age_keeps_its_words_and_replaces_its_numbers(anonymiser):
    invented = anonymiser.age(value="About 45-50")

    assert (invented[:6], invented[8], invented[6:8].isdigit(), invented[9:].isdigit()) == ("About ", "-", True, True)


def test_anonymiser_uid_keeps_its_form_and_is_consistent(anonymiser):
    invented = anonymiser.uid(value="4F2A-93")

    assert (set(invented) <= set("0123456789ABCDEF-"), invented[4], anonymiser.uid(value="4F2A-93")) == (
        True,
        "-",
        invented,
    )


def test_anonymiser_hex_digit_keeps_lower_case(anonymiser):
    assert anonymiser.hex_digit(like="f") in "0123456789abcdef"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("12 MAR 1989", "05 MAR 1979"),
        ("12 Mar 1989", "05 Mar 1979"),
        ("ABT 1989", "ABT 1979"),
        ("BET MAR 1989 AND 1990", "BET MAR 1979 AND 1980"),
        ("12 MAR", "05 MAR"),
        ("29 FEB", "21 FEB"),
        ("31 FEB 1900", "31 FEB 1890"),
        ("9 Mär 1895 oder 9.6.1895", "1 Mär 1885 oder 1.6.1885"),
        ("Oktober 1900", "Oktober 1890"),
        ("1931 (?)", "1921 (?)"),
        ("Frühjahr 1931", "Frühjahr 1921"),
    ],
)
def test_anonymiser_date(anonymiser, value, expected):
    assert anonymiser.date(value=value) == expected


def test_anonymiser_date_keeps_a_german_month_german():
    anonymiser = Anonymiser(rng=random.Random(0), forbidden=set(), offset_days=-40)

    assert anonymiser.date(value="Mär 1900") == "Februar 1900"


def test_anonymiser_date_replaces_the_words_of_a_place(anonymiser):
    invented = anonymiser.date(value="Friedhof Gmunden")

    assert (len(invented), invented[8], invented == "Friedhof Gmunden") == (16, " ", False)


@pytest.mark.parametrize(("name", "expected"), [("MAR", 3), ("Mär", 3), ("Oktober", 10), ("jun", 6)])
def test_month_index(name, expected):
    assert month_index(name=name) == expected


@pytest.mark.parametrize(
    ("like", "index", "expected"),
    [("MAR", 5, "MAY"), ("Mar", 5, "May"), ("Mär", 10, "Okt"), ("Mär", 6, "Juni"), ("März", 6, "Juni")],
)
def test_month_name(like, index, expected):
    assert month_name(like=like, index=index) == expected


def test_refuse_leaks_names_a_word_left_in_a_value():
    document = parse(text="0 @I1@ INDI\n1 NOTE Schmied in Gm\n2 CONC unden\n")

    with pytest.raises(AnonymiseError, match=r"2 replaced words are still in the result: gmunden, schmied."):
        refuse_leaks(document=document, forbidden={"schmied", "unden", "gmunden"})


def test_refuse_leaks_passes_a_clean_document():
    document = parse(text="0 @I1@ INDI\n1 NOTE Abcdefg in Xy\n2 CONC unden\n1 _UID GMUNDEN\n")

    assert refuse_leaks(document=document, forbidden={"schmied", "unden", "gmunden"}) is None


def test_anonymise_keeps_the_structure():
    anonymised = anonymise(text=EXPORT, rng=random.Random(0))

    assert re.sub(r"(?m)^(\d+ (?:@[^@]+@ )?\S+).*$", r"\1", anonymised) == re.sub(
        r"(?m)^(\d+ (?:@[^@]+@ )?\S+).*$", r"\1", EXPORT
    )


def test_main_writes_the_anonymised_file(tmp_path):
    source = tmp_path / "real.ged"
    source.write_bytes(EXPORT.encode("utf-8"))
    target = tmp_path / "anonymised.ged"

    assert (main(argv=[str(source), str(target)]), target.read_bytes()[:9]) == (0, b"\xef\xbb\xbf0 HEAD")


def test_main_writes_nothing_on_an_error(tmp_path, capsys):
    source = tmp_path / "real.ged"
    source.write_bytes(b"0 HEAD\nHuber\n")
    target = tmp_path / "anonymised.ged"

    assert (main(argv=[str(source), str(target)]), target.exists(), capsys.readouterr().err) == (
        1,
        False,
        "Nothing written: Line 2 is not a GEDCOM line.\n",
    )


def test_module_runs_as_a_script(tmp_path):
    source = tmp_path / "real.ged"
    source.write_bytes(EXPORT.encode("utf-8"))
    target = tmp_path / "anonymised.ged"

    with (
        mock.patch.object(sys, "argv", ["anonymise_gedcom", str(source), str(target)]),
        pytest.raises(SystemExit) as exited,
    ):
        runpy.run_path(anonymise_gedcom.__file__, run_name="__main__")

    assert exited.value.code == 0
