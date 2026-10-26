import pytest

from apps.family_tree.models import ParentChild, Person
from apps.family_tree.readers.person import person_entries
from apps.family_tree.readers.person_merge import MergeField, merge_candidates, merge_preview
from apps.family_tree.tests.factories.fact import FactFactory
from apps.family_tree.tests.factories.gedcom_import import GedcomImportFactory
from apps.family_tree.tests.factories.note import NoteFactory
from apps.family_tree.tests.factories.parent_child import ParentChildFactory
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.photo_person import PhotoPersonFactory
from apps.family_tree.tests.factories.source import SourceFactory


@pytest.mark.django_db
def test_merge_candidates_offers_whoever_matches_the_search_but_partners_and_the_line():
    josef = PersonFactory(given_names="Josef", surname="Huber")
    sepp = PersonFactory(given_names="Josef", surname="Huber")
    PersonFactory(given_names="Maria", surname="Huber")
    PartnershipFactory(person_a=josef, person_b=PersonFactory(given_names="Josefa", surname="Huber"))
    ParentChildFactory(parent=PersonFactory(given_names="Josef", surname="Gruber"), child=josef)
    ParentChildFactory(parent=josef, child=PersonFactory(given_names="Josef", surname="Moser"))

    candidates = merge_candidates(pk=josef.pk, search="jos")

    assert candidates == [person_entries(person_ids=[sepp.pk])[sepp.pk]]


@pytest.mark.django_db
def test_merge_candidates_offers_a_sibling():
    josef = ParentChildFactory(child=PersonFactory(given_names="Josef")).child
    sepp = ParentChildFactory(parent=josef.parent_links.get().parent, child=PersonFactory(given_names="Josef")).child

    candidates = merge_candidates(pk=josef.pk, search="Josef")

    assert candidates == [person_entries(person_ids=[sepp.pk])[sepp.pk]]


@pytest.mark.django_db
def test_merge_candidates_offers_nobody_before_anything_is_typed():
    josef = PersonFactory()
    PersonFactory()

    assert merge_candidates(pk=josef.pk, search="") == []


@pytest.mark.django_db
def test_merge_candidates_offers_nobody_for_a_person_who_is_not_there():
    josef = PersonFactory(given_names="Josef")

    assert merge_candidates(pk=josef.pk + 1, search="Josef") == []


@pytest.mark.django_db
def test_merge_preview_shows_both_sides_and_what_differs():
    josef = PersonFactory(given_names="Josef", call_name="", sex=Person.Sex.UNKNOWN)
    sepp = PersonFactory(
        given_names="Josef", call_name="Sepp", sex=Person.Sex.MALE, gedcom_import=GedcomImportFactory(name="MyH")
    )
    FactFactory(person=sepp)
    NoteFactory(person=sepp)
    PhotoPersonFactory(person=sepp)
    SourceFactory(people=[sepp])
    ParentChildFactory(child=sepp)

    preview = merge_preview(pk=josef.pk, other_pk=sepp.pk)

    other = preview.other
    assert (
        preview.fields,
        (other.origin, other.fact_count, other.note_count, other.photo_count, other.source_count),
        (other.relative_count, preview.person.fact_count, preview.person.origin, preview.refusal),
    ) == (
        [
            MergeField(name="given_names", label="Vornamen", text="Josef", other_text="Josef"),
            MergeField(name="surname", label="Familienname", text="Huber", other_text="Huber"),
            MergeField(name="call_name", label="Rufname", text="", other_text="Sepp"),
            MergeField(name="sex", label="Geschlecht", text="unbekannt", other_text="männlich"),
            MergeField(name="living_status", label="Lebensstatus", text="unbekannt", other_text="unbekannt"),
        ],
        ("MyH", 1, 1, 1, 1),
        (1, 0, None, ""),
    )


@pytest.mark.parametrize(("other_text", "differs"), [("Sepp", True), ("", False)])
def test_merge_field_differs_when_the_two_have_different_values(other_text, differs):
    field = MergeField(name="call_name", label="Rufname", text="", other_text=other_text)

    assert field.differs is differs


@pytest.mark.django_db
def test_merge_preview_refuses_a_couple():
    partnership = PartnershipFactory(
        person_a=PersonFactory(given_names="Josef"), person_b=PersonFactory(given_names="Maria")
    )

    preview = merge_preview(pk=partnership.person_a_id, other_pk=partnership.person_b_id)

    assert preview.refusal == "Josef Huber und Maria Huber sind ein Paar, also zwei Personen."


@pytest.mark.parametrize("from_descendant", [True, False])
@pytest.mark.django_db
def test_merge_preview_refuses_an_ancestor_and_their_descendant(from_descendant):
    link = ParentChildFactory(parent=PersonFactory(given_names="Johann"), child=PersonFactory(given_names="Josef"))
    pk, other_pk = (link.child_id, link.parent_id) if from_descendant else (link.parent_id, link.child_id)

    preview = merge_preview(pk=pk, other_pk=other_pk)

    assert preview.refusal == "Johann Huber ist ein Vorfahr von Josef Huber, also sind es zwei Personen."


@pytest.mark.django_db
def test_merge_preview_refuses_more_than_two_birth_parents():
    josef, sepp = PersonFactory(), PersonFactory()
    ParentChildFactory(child=josef)
    johann = ParentChildFactory(child=josef).parent
    ParentChildFactory(parent=johann, child=sepp, pedigree=ParentChild.Pedigree.ADOPTED)
    ParentChildFactory(child=sepp)

    preview = merge_preview(pk=josef.pk, other_pk=sepp.pk)

    assert preview.refusal.startswith("Zusammen hätten die beiden 3 leibliche Eltern.") is True


@pytest.mark.django_db
def test_merge_preview_is_none_for_the_person_and_themselves():
    josef = PersonFactory()

    assert merge_preview(pk=josef.pk, other_pk=josef.pk) is None


@pytest.mark.django_db
def test_merge_preview_is_none_for_somebody_who_is_not_there():
    josef = PersonFactory()

    assert merge_preview(pk=josef.pk, other_pk=josef.pk + 1) is None
