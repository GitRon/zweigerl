import io
import json
from dataclasses import replace
from pathlib import Path

import pytest

from apps.family_tree.actions.gedcom_import import ImportRefusedError, import_gedcom
from apps.family_tree.domain.gedcom import read
from apps.family_tree.domain.gedcom_import import ImportedPerson, ImportedSource, ImportedTree, read_tree
from apps.family_tree.models import (
    Citation,
    Fact,
    GedcomImport,
    Note,
    ParentChild,
    Partnership,
    Person,
    SiblingPair,
    Source,
    TreeSettings,
)
from apps.family_tree.readers.gedcom import gedcom_export
from apps.family_tree.tests.factories.person import PersonFactory

# The anonymised PAF export of #32 - see docs/patterns/testing-data.md. Its values are invented anew on every run
# of the script that writes it, so a test pins forms and counts, never a name or a date.
PAF_EXPORT = Path(__file__).parent.parent / "data" / "paf_export.ged"
# The anonymised MyHeritage export of #84, written the same way.
MYHERITAGE_EXPORT = Path(__file__).parent.parent / "data" / "myheritage_export.ged"


@pytest.mark.django_db
def test_import_gedcom_refuses_a_tree_that_is_not_empty():
    PersonFactory()

    with pytest.raises(ImportRefusedError, match="nur in einen leeren Stammbaum"):
        import_gedcom(file=io.BytesIO(b"0 HEAD\n0 @I1@ INDI\n0 TRLR\n"), name="PAF Huber")


@pytest.mark.django_db
def test_import_gedcom_refuses_a_file_that_is_not_gedcom():
    with pytest.raises(ImportRefusedError, match="keine GEDCOM-Datei"):
        import_gedcom(file=io.BytesIO(b"0 HEAD\nLiebe Oma,\n0 TRLR\n"), name="PAF Huber")


@pytest.mark.django_db
def test_import_gedcom_refuses_an_import_without_a_name_and_writes_nothing():
    with pytest.raises(ImportRefusedError, match="Ein Import braucht einen Namen"):
        import_gedcom(file=io.BytesIO(b"0 HEAD\n0 @I1@ INDI\n0 TRLR\n"), name="  ")

    assert Person.objects.exists() is False


@pytest.mark.django_db
def test_import_gedcom_writes_a_person_with_their_facts_from_the_import():
    file = io.BytesIO(b"0 @I1@ INDI\n1 NAME Lena /Huber/\n1 SEX F\n1 BIRT\n2 DATE 1989\n2 PLAC Graz\n1 _UID 4F2A\n")

    result = import_gedcom(file=file, name="PAF Huber")

    person = Person.objects.get()
    assert (person.given_names, person.sex, person.gedcom_raw, person.gedcom_import) == (
        "Lena",
        "F",
        [{"tag": "_UID", "value": "4F2A"}],
        result.gedcom_import,
    )
    assert list(Fact.objects.values_list("kind", "value", "gedcom_import__name")) == [
        ("birth", "", "PAF Huber"),
        ("birthplace", "Graz", "PAF Huber"),
    ]


@pytest.mark.django_db
def test_import_gedcom_marks_somebody_with_a_death_as_deceased_and_nobody_as_alive():
    file = io.BytesIO(b"0 @I1@ INDI\n1 DEAT Y\n0 @I2@ INDI\n")

    import_gedcom(file=file, name="PAF Huber")

    assert list(Person.objects.order_by("pk").values_list("living_status", flat=True)) == ["deceased", "unknown"]


@pytest.mark.django_db
def test_import_gedcom_makes_the_first_person_of_the_file_the_home_person():
    file = io.BytesIO(b"0 @I7@ INDI\n1 NAME Lena /Huber/\n0 @I1@ INDI\n1 NAME Josef /Huber/\n")

    import_gedcom(file=file, name="PAF Huber")

    assert TreeSettings.objects.get().home_person.given_names == "Lena"


@pytest.mark.django_db
def test_import_gedcom_chooses_no_home_person_from_a_file_without_people():
    result = import_gedcom(file=io.BytesIO(b"0 HEAD\n0 TRLR\n"), name="PAF Huber")

    assert (result.people, TreeSettings.objects.exists()) == (0, False)


@pytest.mark.django_db
def test_import_gedcom_writes_a_couple_with_their_wedding_and_their_child():
    file = io.BytesIO(
        b"0 @I1@ INDI\n0 @I2@ INDI\n0 @I3@ INDI\n"
        b"0 @F1@ FAM\n1 HUSB @I1@\n1 WIFE @I2@\n1 CHIL @I3@\n1 MARR\n2 DATE 1989\n1 _UID 7A\n"
    )

    import_gedcom(file=file, name="PAF Huber")

    partnership = Partnership.objects.get()
    assert (partnership.kind, partnership.gedcom_raw, list(partnership.facts.values_list("kind", flat=True))) == (
        "marriage",
        [{"tag": "_UID", "value": "7A"}],
        ["marriage"],
    )
    assert ParentChild.objects.filter(partnership=partnership, pedigree="birth").count() == 2


@pytest.mark.django_db
def test_import_gedcom_links_the_children_of_a_parent_on_their_own_to_them_alone():
    file = io.BytesIO(b"0 @I1@ INDI\n0 @I2@ INDI\n0 @F1@ FAM\n1 WIFE @I1@\n1 CHIL @I2@\n")

    import_gedcom(file=file, name="PAF Huber")

    assert (Partnership.objects.exists(), ParentChild.objects.get().partnership) == (False, None)


@pytest.mark.django_db
def test_import_gedcom_keeps_what_a_child_link_carries_raw_on_the_first_parent_alone():
    file = io.BytesIO(
        b"0 @I1@ INDI\n0 @I2@ INDI\n0 @I3@ INDI\n1 FAMC @F1@\n2 _UID 9C\n"
        b"0 @F1@ FAM\n1 HUSB @I1@\n1 WIFE @I2@\n1 CHIL @I3@\n"
    )

    import_gedcom(file=file, name="PAF Huber")

    assert list(ParentChild.objects.order_by("parent_id").values_list("gedcom_raw", flat=True)) == [
        [{"tag": "_UID", "value": "9C"}],
        [],
    ]


@pytest.mark.django_db
def test_import_gedcom_counts_only_the_facts_it_wrote():
    file = io.BytesIO(b"0 @I1@ INDI\n1 BIRT\n2 DATE 1960\n0 @F1@ FAM\n1 HUSB @I1@\n1 MARR\n2 DATE 1989\n")

    result = import_gedcom(file=file, name="PAF Huber")

    assert (result.facts, Fact.objects.count()) == (1, 1)


@pytest.mark.django_db
def test_import_gedcom_makes_the_children_of_a_family_without_parents_siblings():
    file = io.BytesIO(b"0 @I1@ INDI\n0 @I2@ INDI\n0 @I3@ INDI\n0 @F1@ FAM\n1 CHIL @I1@\n1 CHIL @I2@\n1 CHIL @I3@\n")

    import_gedcom(file=file, name="PAF Huber")

    assert SiblingPair.objects.count() == 2


@pytest.mark.django_db
def test_import_gedcom_names_the_record_the_models_refuse_and_writes_nothing():
    file = io.BytesIO(
        b"0 @I1@ INDI\n0 @I2@ INDI\n0 @F1@ FAM\n1 HUSB @I1@\n1 WIFE @I2@\n0 @F2@ FAM\n1 HUSB @I2@\n1 WIFE @I1@\n"
    )

    with pytest.raises(ImportRefusedError, match="@F2@ in der Datei: Diese beiden sind schon ein Paar"):
        import_gedcom(file=file, name="PAF Huber")

    assert GedcomImport.objects.exists() is False


@pytest.mark.django_db
def test_import_gedcom_writes_sources_and_the_citations_of_facts_from_the_import():
    file = io.BytesIO(
        b"0 @I1@ INDI\n1 BIRT\n2 DATE 1989\n2 SOUR @S1@\n3 PAGE fol. 12\n3 QUAY 3\n"
        b"0 @S1@ SOUR\n1 TITL Taufbuch Mariazell\n1 AUTH Pfarre\n1 TEXT Band 3, im Pfarrarchiv\n"
    )

    import_gedcom(file=file, name="PAF Huber")

    assert list(Source.objects.values_list("title", "description", "gedcom_raw", "gedcom_import__name")) == [
        ("Taufbuch Mariazell", "Band 3, im Pfarrarchiv", [{"tag": "AUTH", "value": "Pfarre"}], "PAF Huber")
    ]
    assert list(Citation.objects.values_list("fact__kind", "page", "gedcom_raw", "gedcom_import__name")) == [
        ("birth", "fol. 12", [{"tag": "QUAY", "value": "3"}], "PAF Huber")
    ]


@pytest.mark.django_db
def test_import_gedcom_writes_the_citation_of_a_wedding():
    file = io.BytesIO(
        b"0 @I1@ INDI\n0 @I2@ INDI\n0 @F1@ FAM\n1 HUSB @I1@\n1 WIFE @I2@\n1 MARR\n2 DATE 1989\n2 SOUR @S1@\n"
        b"0 @S1@ SOUR\n1 TITL Trauungsbuch\n"
    )

    import_gedcom(file=file, name="PAF Huber")

    assert Citation.objects.get().fact.partnership == Partnership.objects.get()


@pytest.mark.django_db
def test_import_gedcom_documents_a_cited_fact_and_leaves_one_without_a_source_unbelegt():
    file = io.BytesIO(
        b"0 @I1@ INDI\n1 BIRT\n2 DATE 1989\n2 SOUR @S1@\n1 DEAT\n2 DATE 2009\n0 @S1@ SOUR\n1 TITL Taufbuch\n"
    )

    import_gedcom(file=file, name="PAF Huber")

    assert sorted((fact.kind, fact.reliability, fact.is_undocumented) for fact in Fact.objects.all()) == [
        ("birth", "documented", False),
        ("death", "documented", True),
    ]


@pytest.mark.django_db
def test_import_gedcom_leaves_out_a_citation_of_a_source_the_file_does_not_have():
    file = io.BytesIO(b"0 @I1@ INDI\n1 OCCU Uhrmacher\n2 SOUR @S9@\n1 SOUR @S9@\n")

    result = import_gedcom(file=file, name="PAF Huber")

    assert (result.citations, Person.objects.get().filed_sources.exists()) == (0, False)


@pytest.mark.django_db
def test_import_gedcom_files_a_source_with_the_person_pointing_at_it():
    file = io.BytesIO(b"0 @I1@ INDI\n1 SOUR @S1@\n0 @I2@ INDI\n0 @S1@ SOUR\n1 TITL Brief\n")

    import_gedcom(file=file, name="PAF Huber")

    assert list(Source.objects.get().people.values_list("pk", flat=True)) == [Person.objects.order_by("pk")[0].pk]


@pytest.mark.django_db
def test_import_gedcom_writes_the_notes_of_a_person_without_an_author():
    file = io.BytesIO(b"0 @I1@ INDI\n1 NOTE Zwei Jahre in Amerika?\n2 CONT Suchen.\n")

    result = import_gedcom(file=file, name="PAF Huber")

    assert list(Note.objects.values_list("person", "text", "author", "changed_at", "gedcom_import__name")) == [
        (Person.objects.get().pk, "Zwei Jahre in Amerika?\nSuchen.", None, None, "PAF Huber")
    ]
    assert result.notes == 1


@pytest.mark.django_db
def test_import_gedcom_reads_the_paf_export():
    with PAF_EXPORT.open("rb") as file:
        result = import_gedcom(file=file, name="PAF Huber")

    assert (result.people, result.families, result.sources, result.citations, result.notes) == (412, 163, 2, 2, 44)
    assert (Person.objects.count(), Partnership.objects.count()) == (412, 150)


@pytest.mark.django_db
def test_import_gedcom_reads_the_myheritage_export():
    with MYHERITAGE_EXPORT.open("rb") as file:
        result = import_gedcom(file=file, name="MyHeritage Huber")

    assert (result.people, result.families, result.sources, result.citations) == (171, 75, 1, 0)
    assert (
        Person.objects.filter(living_status=Person.LivingStatus.DECEASED).count(),
        Source.objects.get().people.count(),
    ) == (110, 49)


@pytest.mark.django_db
def test_import_gedcom_takes_the_reliability_of_a_fact_from_the_quay_of_its_citation():
    file = io.BytesIO(b"0 @I1@ INDI\n1 OCCU Uhrmacher\n2 SOUR @S1@\n3 QUAY 1\n0 @S1@ SOUR\n1 TITL Brief\n")

    import_gedcom(file=file, name="MyHeritage Huber")

    fact = Fact.objects.get()
    assert (fact.reliability, fact.citations.get().gedcom_raw) == ("probable", [{"tag": "QUAY", "value": "1"}])


@pytest.mark.django_db
@pytest.mark.parametrize("export", [PAF_EXPORT, MYHERITAGE_EXPORT], ids=["paf", "myheritage"])
def test_import_gedcom_gets_back_what_the_export_writes_of_a_program_export(export):
    """
    The round trip of #22, #23 and #84: an export imported and exported again reads as the same people, families
    and sources - their names, facts, citations, notes and everything kept raw. Compared as text, not as lines:
    the export cuts a long value beside a space, PAF in the middle of a word, and writes the records in an order
    of its own.
    """
    with export.open("rb") as file:
        original = read_tree(records=read(file=file))
        import_gedcom(file=file, name="PAF Huber")

    exported = read_tree(records=read(file=io.BytesIO(gedcom_export().encode())))

    assert _people(tree=exported) == _people(tree=original)
    assert _families(tree=exported) == _families(tree=original)
    assert _sources(tree=exported) == _sources(tree=original)


def _people(*, tree: ImportedTree) -> list[ImportedPerson]:
    """
    Without the xrefs, which are the file's own - a citation and a filed source name their source by its title
    instead - and with the facts and the raw structures in one order: the export writes the raw parts of a name
    into its own NAME, which comes first, where MyHeritage writes a "_UPD" before it.
    """
    titles = {source.xref: source.title for source in tree.sources}
    return [
        replace(
            person,
            xref="",
            raw=sorted(person.raw, key=lambda structure: json.dumps(structure, sort_keys=True)),
            facts=sorted(
                (
                    replace(
                        fact,
                        citations=[replace(citation, source=titles[citation.source]) for citation in fact.citations],
                    )
                    for fact in person.facts
                ),
                key=lambda fact: (fact.kind, fact.value, str(fact.date)),
            ),
            sources=[titles[xref] for xref in person.sources],
        )
        for person in tree.people
    ]


def _sources(*, tree: ImportedTree) -> list[ImportedSource]:
    return sorted((replace(source, xref="") for source in tree.sources), key=lambda source: source.title)


def _families(*, tree: ImportedTree) -> list[tuple]:
    """
    The families by the places of their members among the people. A parent on their own has no row to keep what
    their family carries - its "_UID", a "MARR" - so only a couple's wedding and raw are compared, and a parent on
    their own without children, which leaves no row at all, is not compared.
    """
    place = {person.xref: index for index, person in enumerate(tree.people)}
    families = [
        (
            tuple(sorted(place[xref] for xref in family.parents)),
            sorted((place[child.xref], child.pedigree, child.raw) for child in family.children),
            family.married if len(family.parents) == 2 else False,
            sorted(family.facts, key=lambda fact: (fact.kind, str(fact.date))),
            family.raw if len(family.parents) == 2 else [],
        )
        for family in tree.families
        if len(family.parents) == 2 or family.children
    ]
    return sorted(families, key=lambda family: family[0])
