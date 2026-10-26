import datetime
import io

import pytest

from apps.family_tree.domain.dates import DateKind, Precision, UncertainDate
from apps.family_tree.domain.gedcom import read
from apps.family_tree.domain.gedcom_import import (
    ImportedChild,
    ImportedCitation,
    ImportedFact,
    ImportedFamily,
    ImportedNote,
    ImportedPerson,
    ImportedSource,
    ImportedTree,
    read_date,
    read_tree,
)

# Every file below is invented, after the Familie Huber - see docs/patterns/testing-data.md.
MARCH_12_1931 = UncertainDate(kind=DateKind.EXACT, date_1=datetime.date(1931, 3, 12), precision=Precision.DAY)
YEAR_1989 = UncertainDate(kind=DateKind.EXACT, date_1=datetime.date(1989, 1, 1), precision=Precision.YEAR)


def test_read_tree_reads_people_families_and_sources_and_leaves_out_the_rest():
    records = read(
        file=io.BytesIO(b"0 HEAD\n0 @I1@ INDI\n0 @F1@ FAM\n0 @S1@ SOUR\n1 TITL Taufbuch\n0 @N1@ NOTE Lose\n0 TRLR\n")
    )

    tree = read_tree(records=records)

    assert tree == ImportedTree(
        people=[ImportedPerson(xref="@I1@")],
        families=[ImportedFamily(xref="@F1@", parents=())],
        sources=[ImportedSource(xref="@S1@", title="Taufbuch")],
    )


def test_read_tree_reads_a_source_with_its_text_and_keeps_the_rest_raw():
    records = read(file=io.BytesIO(b"0 @S1@ SOUR\n1 TITL Taufbuch\n1 AUTH Pfarre Mariazell\n1 TEXT Band 3\n"))

    tree = read_tree(records=records)

    assert tree.sources == [
        ImportedSource(
            xref="@S1@",
            title="Taufbuch",
            description="Band 3",
            raw=[{"tag": "AUTH", "value": "Pfarre Mariazell"}],
        )
    ]


def test_read_tree_names_a_source_without_a_title_after_its_record():
    records = read(file=io.BytesIO(b"0 @S1@ SOUR\n1 TITL\n"))

    tree = read_tree(records=records)

    assert tree.sources == [ImportedSource(xref="@S1@", title="Quelle @S1@", raw=[{"tag": "TITL"}])]


def test_read_tree_keeps_a_title_too_long_for_a_source_raw():
    title = "Taufbuch " * 40
    records = read(file=io.BytesIO(f"0 @S1@ SOUR\n1 TITL {title}\n".encode()))

    tree = read_tree(records=records)

    assert tree.sources == [ImportedSource(xref="@S1@", title="Quelle @S1@", raw=[{"tag": "TITL", "value": title}])]


def test_read_tree_reads_a_citation_with_its_page_and_keeps_the_rest_raw():
    records = read(
        file=io.BytesIO(b"0 @I1@ INDI\n1 DEAT\n2 DATE 1989\n2 SOUR @S1@\n3 PAGE fol. 12\n3 QUAY 3\n2 SOUR Brief\n")
    )

    tree = read_tree(records=records)

    assert tree.people[0].facts == [
        ImportedFact(
            kind="death",
            date=YEAR_1989,
            citations=[
                ImportedCitation(source="@S1@", page="fol. 12", quality="3", raw=[{"tag": "QUAY", "value": "3"}])
            ],
            raw=[{"tag": "SOUR", "value": "Brief"}],
        )
    ]


@pytest.mark.parametrize(
    ("quay", "reliability"),
    [("3", "documented"), ("2", "documented"), ("1", "probable"), ("0", "handed_down"), ("hoch", "documented")],
)
def test_read_tree_takes_the_reliability_of_a_fact_from_the_quay_of_its_citation(quay, reliability):
    records = read(file=io.BytesIO(f"0 @I1@ INDI\n1 OCCU Uhrmacher\n2 SOUR @S1@\n3 QUAY {quay}\n".encode()))

    tree = read_tree(records=records)

    assert tree.people[0].facts[0].reliability == reliability


def test_read_tree_takes_the_best_quay_of_the_citations_of_a_fact():
    records = read(
        file=io.BytesIO(
            b"0 @I1@ INDI\n1 OCCU Uhrmacher\n2 SOUR @S1@\n3 QUAY 0\n2 SOUR @S2@\n3 QUAY 1\n2 SOUR @S1@\n3 QUAY 0\n"
        )
    )

    tree = read_tree(records=records)

    fact = tree.people[0].facts[0]
    assert ([citation.quality for citation in fact.citations], fact.reliability) == (["0", "1"], "probable")


def test_read_tree_takes_the_better_quay_of_one_source_cited_twice():
    records = read(
        file=io.BytesIO(b"0 @I1@ INDI\n1 OCCU Uhrmacher\n2 SOUR @S1@\n3 QUAY 0\n2 SOUR @S1@\n3 QUAY 2\n")
    )

    tree = read_tree(records=records)

    assert tree.people[0].facts[0].citations[0].quality == "2"


def test_read_tree_leaves_a_fact_without_a_quay_documented():
    records = read(file=io.BytesIO(b"0 @I1@ INDI\n1 OCCU Uhrmacher\n2 SOUR @S1@\n"))

    tree = read_tree(records=records)

    assert tree.people[0].facts[0].reliability == "documented"


def test_read_tree_joins_the_pages_of_one_source_cited_twice_by_a_fact():
    records = read(
        file=io.BytesIO(b"0 @I1@ INDI\n1 OCCU Uhrmacher\n2 SOUR @S1@\n3 PAGE fol. 12\n2 SOUR @S1@\n3 PAGE fol. 14\n")
    )

    tree = read_tree(records=records)

    assert tree.people[0].facts[0].citations == [ImportedCitation(source="@S1@", page="fol. 12; fol. 14")]


def test_read_tree_keeps_a_page_too_long_for_a_citation_raw():
    page = "fol. 12 " * 40
    records = read(file=io.BytesIO(f"0 @I1@ INDI\n1 OCCU Uhrmacher\n2 SOUR @S1@\n3 PAGE {page}\n".encode()))

    tree = read_tree(records=records)

    assert tree.people[0].facts[0].citations == [ImportedCitation(source="@S1@", raw=[{"tag": "PAGE", "value": page}])]


def test_read_tree_gives_the_citations_of_a_birth_to_its_date():
    records = read(file=io.BytesIO(b"0 @I1@ INDI\n1 BIRT\n2 DATE 1989\n2 PLAC Graz\n2 SOUR @S1@\n"))

    tree = read_tree(records=records)

    birth, place = tree.people[0].facts
    assert (birth.citations, place.citations) == ([ImportedCitation(source="@S1@")], [])


def test_read_tree_gives_the_citations_of_a_birth_without_a_date_to_its_place():
    records = read(file=io.BytesIO(b"0 @I1@ INDI\n1 BIRT\n2 PLAC Graz\n2 SOUR @S1@\n"))

    tree = read_tree(records=records)

    assert tree.people[0].facts[0].citations == [ImportedCitation(source="@S1@")]


def test_read_tree_reads_the_citation_of_a_wedding():
    records = read(file=io.BytesIO(b"0 @F1@ FAM\n1 MARR\n2 DATE 1989\n2 SOUR @S1@\n"))

    tree = read_tree(records=records)

    assert tree.families[0].facts[0].citations == [ImportedCitation(source="@S1@")]


def test_read_tree_files_a_source_pointed_at_from_a_person_with_them():
    records = read(file=io.BytesIO(b"0 @I1@ INDI\n1 SOUR @S1@\n1 SOUR Brief von Tante Resi\n"))

    tree = read_tree(records=records)

    assert (tree.people[0].sources, tree.people[0].raw) == (
        ["@S1@"],
        [{"tag": "SOUR", "value": "Brief von Tante Resi"}],
    )


def test_read_tree_keeps_what_a_source_pointed_at_from_a_person_carries_raw_without_the_pointer():
    records = read(
        file=io.BytesIO(
            b"0 @I1@ INDI\n1 SOUR @S1@\n2 PAGE Lena Huber\n2 QUAY 3\n2 DATA\n3 DATE 5 MAR 2006\n3 TEXT Bestaetigt\n"
        )
    )

    tree = read_tree(records=records)

    assert (tree.people[0].sources, tree.people[0].raw) == (
        ["@S1@"],
        [
            {
                "tag": "SOUR",
                "children": [
                    {"tag": "PAGE", "value": "Lena Huber"},
                    {"tag": "QUAY", "value": "3"},
                    {
                        "tag": "DATA",
                        "children": [{"tag": "DATE", "value": "5 MAR 2006"}, {"tag": "TEXT", "value": "Bestaetigt"}],
                    },
                ],
            }
        ],
    )


def test_read_tree_reads_a_note_on_a_person_with_what_it_carries_raw():
    records = read(file=io.BytesIO(b"0 @I1@ INDI\n1 NOTE Zwei Jahre i\n2 CONC n Amerika?\n2 CONT Suchen.\n2 _X 1\n"))

    tree = read_tree(records=records)

    assert tree.people[0].notes == [
        ImportedNote(text="Zwei Jahre in Amerika?\nSuchen.", raw=[{"tag": "_X", "value": "1"}])
    ]


def test_read_tree_reads_a_note_pointing_at_a_note_record():
    records = read(
        file=io.BytesIO(b"0 @I1@ INDI\n1 NOTE @N1@\n0 @N1@ NOTE Zwei Jahre in Amerika?\n1 CHAN\n2 DATE 1 JAN 2000\n")
    )

    tree = read_tree(records=records)

    assert tree.people[0].notes == [
        ImportedNote(
            text="Zwei Jahre in Amerika?",
            raw=[{"tag": "CHAN", "children": [{"tag": "DATE", "value": "1 JAN 2000"}]}],
        )
    ]


def test_read_tree_leaves_out_a_note_pointing_at_a_record_the_file_does_not_have():
    records = read(file=io.BytesIO(b"0 @I1@ INDI\n1 NOTE @N9@\n"))

    tree = read_tree(records=records)

    assert tree.people[0] == ImportedPerson(xref="@I1@")


def test_read_tree_keeps_a_note_without_text_raw():
    records = read(file=io.BytesIO(b"0 @I1@ INDI\n1 NOTE \n2 _X 1\n"))

    tree = read_tree(records=records)

    assert (tree.people[0].notes, tree.people[0].raw) == (
        [],
        [{"tag": "NOTE", "children": [{"tag": "_X", "value": "1"}]}],
    )


def test_read_tree_keeps_a_note_on_a_family_raw():
    records = read(file=io.BytesIO(b"0 @F1@ FAM\n1 NOTE Kennengelernt am Kirtag\n"))

    tree = read_tree(records=records)

    assert tree.families[0].raw == [{"tag": "NOTE", "value": "Kennengelernt am Kirtag"}]


def test_read_tree_gives_a_divorce_on_a_person_to_their_only_family():
    records = read(file=io.BytesIO(b"0 @I1@ INDI\n1 FAMS @F1@\n1 DIV\n2 DATE 1989\n0 @F1@ FAM\n1 HUSB @I1@\n"))

    tree = read_tree(records=records)

    assert tree.families[0].facts == [ImportedFact(kind="divorce", date=YEAR_1989)]


def test_read_tree_keeps_a_divorce_raw_on_a_person_with_two_families():
    records = read(file=io.BytesIO(b"0 @I1@ INDI\n1 FAMS @F1@\n1 FAMS @F2@\n1 DIV\n0 @F1@ FAM\n0 @F2@ FAM\n"))

    tree = read_tree(records=records)

    assert tree.people[0].raw == [{"tag": "DIV"}]


def test_read_tree_takes_a_death_for_deceased():
    tree = read_tree(records=read(file=io.BytesIO(b"0 @I1@ INDI\n1 DEAT Y\n")))

    assert tree.people[0] == ImportedPerson(xref="@I1@", deceased=True)


def test_read_tree_takes_a_burial_for_deceased():
    tree = read_tree(records=read(file=io.BytesIO(b"0 @I1@ INDI\n1 BURI\n2 PLAC Mariazell\n")))

    assert tree.people[0].deceased is True


def test_read_tree_never_takes_somebody_without_a_death_for_alive():
    tree = read_tree(records=read(file=io.BytesIO(b"0 @I1@ INDI\n1 BIRT\n2 DATE 1820\n")))

    assert tree.people[0].deceased is False


def test_read_tree_keeps_a_tag_it_does_not_know_raw_without_its_pointers():
    records = read(file=io.BytesIO(b"0 @I1@ INDI\n1 _UID 4F2A\n1 SOUR @S1@\n1 RELI rk.\n2 SOUR @S1@\n"))

    tree = read_tree(records=records)

    assert tree.people[0].raw == [{"tag": "_UID", "value": "4F2A"}, {"tag": "RELI", "value": "rk."}]


def test_read_tree_reads_the_parts_of_a_name():
    records = read(
        file=io.BytesIO(
            b"0 @I1@ INDI\n1 NAME Maria Theresia /Huber/\n2 GIVN Maria Theresia\n2 SURN Huber\n2 NICK Resi\n"
        )
    )

    person = read_tree(records=records).people[0]

    assert (person.given_names, person.surname, person.call_name, person.raw) == ("Maria Theresia", "Huber", "Resi", [])


def test_read_tree_reads_a_name_without_its_parts_from_the_slashes():
    person = read_tree(records=read(file=io.BytesIO(b"0 @I1@ INDI\n1 NAME Lena /Huber/\n"))).people[0]

    assert (person.given_names, person.surname) == ("Lena", "Huber")


def test_read_tree_reads_an_empty_surname_as_empty():
    person = read_tree(records=read(file=io.BytesIO(b"0 @I1@ INDI\n1 NAME Theresia //\n"))).people[0]

    assert (person.given_names, person.surname) == ("Theresia", "")


def test_read_tree_keeps_a_surname_nobody_knows_as_written():
    person = read_tree(records=read(file=io.BytesIO(b"0 @I1@ INDI\n1 NAME Anna /?/\n"))).people[0]

    assert person.surname == "?"


def test_read_tree_reads_a_name_without_slashes_as_given_names():
    person = read_tree(records=read(file=io.BytesIO(b"0 @I1@ INDI\n1 NAME Anna\n"))).people[0]

    assert (person.given_names, person.surname) == ("Anna", "")


def test_read_tree_keeps_the_other_parts_of_a_name_raw_as_a_name_without_value():
    records = read(file=io.BytesIO(b"0 @I1@ INDI\n1 NAME Lena /Huber/\n2 NPFX Dr.\n2 _MARNM Maier\n"))

    person = read_tree(records=records).people[0]

    assert person.raw == [
        {"tag": "NAME", "children": [{"tag": "NPFX", "value": "Dr."}, {"tag": "_MARNM", "value": "Maier"}]}
    ]


def test_read_tree_keeps_a_second_name_raw_whole():
    person = read_tree(
        records=read(file=io.BytesIO(b"0 @I1@ INDI\n1 NAME Lena /Huber/\n1 NAME Lene /Maier/\n"))
    ).people[0]

    assert (person.given_names, person.raw) == ("Lena", [{"tag": "NAME", "value": "Lene /Maier/"}])


def test_read_tree_reads_the_sex():
    assert read_tree(records=read(file=io.BytesIO(b"0 @I1@ INDI\n1 SEX F\n"))).people[0].sex == "F"


def test_read_tree_keeps_a_sex_it_does_not_know_raw():
    person = read_tree(records=read(file=io.BytesIO(b"0 @I1@ INDI\n1 SEX N\n"))).people[0]

    assert (person.sex, person.raw) == ("U", [{"tag": "SEX", "value": "N"}])


def test_read_tree_splits_a_birth_into_its_date_and_its_place():
    records = read(file=io.BytesIO(b"0 @I1@ INDI\n1 BIRT\n2 DATE 12 Mar 1931\n2 PLAC Graz\n2 NOTE Hausgeburt\n"))

    facts = read_tree(records=records).people[0].facts

    assert facts == [
        ImportedFact(kind="birth", date=MARCH_12_1931, raw=[{"tag": "NOTE", "value": "Hausgeburt"}]),
        ImportedFact(kind="birthplace", value="Graz"),
    ]


def test_read_tree_keeps_a_birth_date_it_cannot_read_raw_below_the_birthplace():
    records = read(file=io.BytesIO(b"0 @I1@ INDI\n1 BIRT\n2 DATE Fruehjahr 1931\n2 PLAC Graz\n"))

    facts = read_tree(records=records).people[0].facts

    assert facts == [ImportedFact(kind="birthplace", value="Graz", raw=[{"tag": "DATE", "value": "Fruehjahr 1931"}])]


def test_read_tree_keeps_a_birth_without_date_or_place_raw():
    person = read_tree(records=read(file=io.BytesIO(b"0 @I1@ INDI\n1 BIRT\n2 DATE im Krieg\n"))).people[0]

    assert (person.facts, person.raw) == ([], [{"tag": "BIRT", "children": [{"tag": "DATE", "value": "im Krieg"}]}])


def test_read_tree_keeps_a_birthplace_too_long_for_a_fact_raw_below_the_birth():
    place = "Graz " * 61
    records = read(file=io.BytesIO(f"0 @I1@ INDI\n1 BIRT\n2 DATE 12 MAR 1931\n2 PLAC {place}\n".encode()))

    facts = read_tree(records=records).people[0].facts

    assert facts == [ImportedFact(kind="birth", date=MARCH_12_1931, raw=[{"tag": "PLAC", "value": place}])]


def test_read_tree_reads_an_event_with_its_date_and_keeps_its_place_raw():
    records = read(file=io.BytesIO(b"0 @I1@ INDI\n1 CHR\n2 DATE 12 MAR 1931\n2 PLAC Mariazell\n"))

    facts = read_tree(records=records).people[0].facts

    assert facts == [ImportedFact(kind="baptism", date=MARCH_12_1931, raw=[{"tag": "PLAC", "value": "Mariazell"}])]


def test_read_tree_keeps_an_event_with_a_date_it_cannot_read_raw_whole():
    person = read_tree(records=read(file=io.BytesIO(b"0 @I1@ INDI\n1 DEAT\n2 DATE 1926 (?)\n"))).people[0]

    assert (person.facts, person.raw) == ([], [{"tag": "DEAT", "children": [{"tag": "DATE", "value": "1926 (?)"}]}])


def test_read_tree_reads_an_occupation_and_keeps_its_date_raw():
    records = read(file=io.BytesIO(b"0 @I1@ INDI\n1 OCCU Uhrmacher\n2 DATE 1871\n"))

    facts = read_tree(records=records).people[0].facts

    assert facts == [ImportedFact(kind="occupation", value="Uhrmacher", raw=[{"tag": "DATE", "value": "1871"}])]


def test_read_tree_keeps_an_occupation_without_value_raw():
    person = read_tree(records=read(file=io.BytesIO(b"0 @I1@ INDI\n1 OCCU\n2 PLAC Graz\n"))).people[0]

    assert (person.facts, person.raw) == ([], [{"tag": "OCCU", "children": [{"tag": "PLAC", "value": "Graz"}]}])


def test_read_tree_keeps_a_family_link_without_a_pointer_raw():
    person = read_tree(records=read(file=io.BytesIO(b"0 @I1@ INDI\n1 FAMS\n1 FAMC\n"))).people[0]

    assert person.raw == [{"tag": "FAMS"}, {"tag": "FAMC"}]


def test_read_tree_reads_a_couple_with_their_wedding_and_their_child():
    records = read(
        file=io.BytesIO(
            b"0 @F1@ FAM\n1 HUSB @I1@\n1 WIFE @I2@\n1 CHIL @I3@\n1 MARR\n2 DATE 12 MAR 1931\n2 PLAC Graz\n1 _UID 7A\n"
        )
    )

    family = read_tree(records=records).families[0]

    assert (family.parents, family.children, family.married, family.facts, family.raw) == (
        ("@I1@", "@I2@"),
        [ImportedChild(xref="@I3@")],
        True,
        [ImportedFact(kind="marriage", date=MARCH_12_1931, raw=[{"tag": "PLAC", "value": "Graz"}])],
        [{"tag": "_UID", "value": "7A"}],
    )


def test_read_tree_keeps_a_wedding_without_a_date_raw_and_the_couple_married():
    family = read_tree(records=read(file=io.BytesIO(b"0 @F1@ FAM\n1 MARR\n2 PLAC Graz\n"))).families[0]

    assert (family.married, family.raw) == (True, [{"tag": "MARR", "children": [{"tag": "PLAC", "value": "Graz"}]}])


def test_read_tree_takes_a_wedding_that_says_only_that_it_happened_for_the_kind():
    family = read_tree(records=read(file=io.BytesIO(b"0 @F1@ FAM\n1 MARR Y\n"))).families[0]

    assert (family.married, family.facts, family.raw) == (True, [], [])


def test_read_tree_keeps_a_divorce_without_a_date_raw():
    family = read_tree(records=read(file=io.BytesIO(b"0 @F1@ FAM\n1 DIV Y\n"))).families[0]

    assert (family.married, family.raw) == (False, [{"tag": "DIV", "value": "Y"}])


def test_read_tree_keeps_a_family_link_of_the_family_without_a_pointer_raw():
    family = read_tree(records=read(file=io.BytesIO(b"0 @F1@ FAM\n1 HUSB\n"))).families[0]

    assert (family.parents, family.raw) == ((), [{"tag": "HUSB"}])


def test_read_tree_reads_the_pedigree_of_a_child_from_its_family_link():
    records = read(file=io.BytesIO(b"0 @I3@ INDI\n1 FAMC @F1@\n2 PEDI adopted\n0 @F1@ FAM\n1 CHIL @I3@\n"))

    assert read_tree(records=records).families[0].children == [ImportedChild(xref="@I3@", pedigree="adopted")]


def test_read_tree_keeps_a_pedigree_it_has_no_word_for_raw():
    records = read(file=io.BytesIO(b"0 @I3@ INDI\n1 FAMC @F1@\n2 PEDI sealing\n0 @F1@ FAM\n1 CHIL @I3@\n"))

    children = read_tree(records=records).families[0].children

    assert children == [ImportedChild(xref="@I3@", pedigree="unknown", raw=[{"tag": "PEDI", "value": "sealing"}])]


def test_read_tree_keeps_what_a_child_link_carries_raw():
    records = read(
        file=io.BytesIO(b"0 @I3@ INDI\n1 FAMC @F1@\n2 NOTE vom Hof\n0 @F1@ FAM\n1 CHIL @I3@\n2 _FREL Natural\n")
    )

    children = read_tree(records=records).families[0].children

    assert children == [
        ImportedChild(xref="@I3@", raw=[{"tag": "NOTE", "value": "vom Hof"}, {"tag": "_FREL", "value": "Natural"}])
    ]


def test_read_tree_reads_a_day_written_the_german_way():
    records = read(file=io.BytesIO(b"0 @I1@ INDI\n1 DEAT\n2 DATE 12.03.1931\n"))

    tree = read_tree(records=records)

    assert tree.people[0].facts == [ImportedFact(kind="death", date=MARCH_12_1931)]


@pytest.mark.parametrize("text", ["12.03.1931", "12.3.1931", " 12.03.1931 ", "12 MAR 1931"])
def test_read_date_reads_gedcom_and_a_day_written_the_german_way(text):
    assert read_date(text=text) == MARCH_12_1931


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("31.02.1931", "kein gültiges Datum"),
        ("12 03.1931", "kein Datum, das Zweigerl lesen kann"),
        ("TO 12 MAR 1931", "kein Datum, das Zweigerl lesen kann"),
    ],
)
def test_read_date_refuses_what_it_cannot_read(text, message):
    with pytest.raises(ValueError, match=message):
        read_date(text=text)
