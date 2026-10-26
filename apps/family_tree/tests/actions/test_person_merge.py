import pytest
from django.core.exceptions import ValidationError

from apps.family_tree.actions.person_merge import merge_persons
from apps.family_tree.models import Fact, ParentChild, Partnership, Person, PhotoPerson, SiblingPair, TreeSettings
from apps.family_tree.tests.factories.citation import CitationFactory
from apps.family_tree.tests.factories.fact import FactFactory
from apps.family_tree.tests.factories.gedcom_import import GedcomImportFactory
from apps.family_tree.tests.factories.note import NoteFactory
from apps.family_tree.tests.factories.parent_child import ParentChildFactory
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.photo_person import PhotoPersonFactory
from apps.family_tree.tests.factories.sibling_pair import SiblingPairFactory
from apps.family_tree.tests.factories.source import SourceFactory
from apps.family_tree.tests.factories.tree_settings import TreeSettingsFactory


@pytest.mark.django_db
def test_merge_persons_takes_the_chosen_fields_from_the_other_and_deletes_them():
    josef = PersonFactory(given_names="Josef", surname="Huber", call_name="", sex=Person.Sex.UNKNOWN)
    sepp = PersonFactory(given_names="Josef Anton", surname="Huber", call_name="Sepp", sex=Person.Sex.MALE)

    merged = merge_persons(person_id=josef.pk, other_id=sepp.pk, from_other=["call_name", "sex"])

    assert (
        list(Person.objects.values_list("pk", "given_names", "call_name", "sex")),
        merged,
    ) == ([(josef.pk, "Josef", "Sepp", Person.Sex.MALE)], josef)


@pytest.mark.django_db
def test_merge_persons_keeps_what_both_kept_raw_and_the_herkunft_of_the_person():
    paf = GedcomImportFactory(name="PAF Huber")
    josef = PersonFactory(gedcom_import=paf, gedcom_raw=[{"tag": "_UID", "value": "4F2A"}])
    other = PersonFactory(
        gedcom_import=GedcomImportFactory(name="MyHeritage Huber"), gedcom_raw=[{"tag": "RIN", "value": "7"}]
    )

    merge_persons(person_id=josef.pk, other_id=other.pk, from_other=[])

    josef.refresh_from_db()
    assert (josef.gedcom_raw, josef.gedcom_import) == (
        [{"tag": "_UID", "value": "4F2A"}, {"tag": "RIN", "value": "7"}],
        paf,
    )


@pytest.mark.django_db
def test_merge_persons_keeps_both_facts_with_their_citations_and_herkunft():
    josef, other = PersonFactory(), PersonFactory()
    FactFactory(person=josef)
    myheritage = GedcomImportFactory(name="MyHeritage Huber")
    citation = CitationFactory(fact=FactFactory(person=other, gedcom_import=myheritage))

    merge_persons(person_id=josef.pk, other_id=other.pk, from_other=[])

    assert (
        Fact.objects.filter(person=josef, kind=Fact.Kind.BIRTH).count(),
        Fact.objects.get(citations=citation).gedcom_import,
    ) == (2, myheritage)


@pytest.mark.django_db
def test_merge_persons_moves_the_notes_and_files_the_sources_with_the_person():
    josef, other = PersonFactory(), PersonFactory()
    note = NoteFactory(person=other)
    source = SourceFactory(people=[other])

    merge_persons(person_id=josef.pk, other_id=other.pk, from_other=[])

    assert (list(josef.notes.all()), list(josef.filed_sources.all())) == ([note], [source])


@pytest.mark.django_db
def test_merge_persons_keeps_the_portrait_of_the_person():
    josef, other = PersonFactory(), PersonFactory()
    portrait = PhotoPersonFactory(person=josef, is_portrait=True)
    other_portrait = PhotoPersonFactory(person=other, is_portrait=True)

    merge_persons(person_id=josef.pk, other_id=other.pk, from_other=[])

    assert list(PhotoPerson.objects.filter(person=josef).values_list("photo", "is_portrait")) == [
        (portrait.photo_id, True),
        (other_portrait.photo_id, False),
    ]


@pytest.mark.django_db
def test_merge_persons_puts_a_photo_of_both_on_the_person_once_with_the_others_portrait():
    josef, other = PersonFactory(), PersonFactory()
    link = PhotoPersonFactory(person=josef)
    PhotoPersonFactory(photo=link.photo, person=other, is_portrait=True)

    merge_persons(person_id=josef.pk, other_id=other.pk, from_other=[])

    assert list(PhotoPerson.objects.values_list("pk", "is_portrait")) == [(link.pk, True)]


@pytest.mark.django_db
def test_merge_persons_makes_the_person_the_home_person_in_place_of_the_other():
    josef = PersonFactory()
    settings = TreeSettingsFactory()

    merge_persons(person_id=josef.pk, other_id=settings.home_person_id, from_other=[])

    assert TreeSettings.objects.get().home_person == josef


@pytest.mark.django_db
def test_merge_persons_gives_a_partnership_of_the_other_to_the_person():
    josef, other = PersonFactory(), PersonFactory()
    partnership = PartnershipFactory(person_a=PersonFactory(given_names="Maria"), person_b=other)
    ParentChildFactory(parent=other, child=PersonFactory(), partnership=partnership)

    merge_persons(person_id=josef.pk, other_id=other.pk, from_other=[])

    assert list(ParentChild.objects.values_list("parent", "partnership")) == [(josef.pk, partnership.pk)]


@pytest.mark.django_db
def test_merge_persons_makes_one_family_of_two_with_the_same_partner():
    josef, other, maria = PersonFactory(), PersonFactory(), PersonFactory(given_names="Maria")
    family = PartnershipFactory(person_a=josef, person_b=maria, kind=Partnership.Kind.UNKNOWN)
    other_family = PartnershipFactory(person_a=maria, person_b=other, gedcom_raw=[{"tag": "_UID", "value": "F1"}])
    FactFactory(person=None, partnership=other_family, kind=Fact.Kind.MARRIAGE)
    anna = ParentChildFactory(parent=josef, child=PersonFactory(given_names="Anna"), partnership=family).child
    franz = PersonFactory(given_names="Franz")
    ParentChildFactory(parent=other, child=franz, partnership=other_family)
    ParentChildFactory(parent=maria, child=franz, partnership=other_family)

    merge_persons(person_id=josef.pk, other_id=other.pk, from_other=[])

    family.refresh_from_db()
    assert (
        list(Partnership.objects.values_list("pk", "kind", "gedcom_raw")),
        family.facts.count(),
        set(ParentChild.objects.values_list("parent", "child", "partnership")),
    ) == (
        [(family.pk, Partnership.Kind.MARRIAGE, [{"tag": "_UID", "value": "F1"}])],
        1,
        {(josef.pk, anna.pk, family.pk), (josef.pk, franz.pk, family.pk), (maria.pk, franz.pk, family.pk)},
    )


@pytest.mark.django_db
def test_merge_persons_keeps_a_child_of_both_once_with_the_raw_of_both_links():
    josef, other, anna = PersonFactory(), PersonFactory(), PersonFactory()
    link = ParentChildFactory(parent=josef, child=anna, gedcom_raw=[{"tag": "_FREL", "value": "Natural"}])
    ParentChildFactory(parent=other, child=anna, gedcom_raw=[{"tag": "_MREL", "value": "Natural"}])

    merge_persons(person_id=josef.pk, other_id=other.pk, from_other=[])

    assert list(ParentChild.objects.values_list("pk", "gedcom_raw")) == [
        (link.pk, [{"tag": "_FREL", "value": "Natural"}, {"tag": "_MREL", "value": "Natural"}])
    ]


@pytest.mark.django_db
def test_merge_persons_keeps_a_parent_of_both_once_and_adds_the_others_parent():
    josef, other = PersonFactory(), PersonFactory()
    johann, theresia = PersonFactory(given_names="Johann"), PersonFactory(given_names="Theresia")
    ParentChildFactory(parent=johann, child=josef)
    ParentChildFactory(parent=johann, child=other, pedigree=ParentChild.Pedigree.ADOPTED)
    ParentChildFactory(parent=theresia, child=other)

    merge_persons(person_id=josef.pk, other_id=other.pk, from_other=[])

    assert set(ParentChild.objects.values_list("parent", "child", "pedigree")) == {
        (johann.pk, josef.pk, ParentChild.Pedigree.BIRTH),
        (theresia.pk, josef.pk, ParentChild.Pedigree.BIRTH),
    }


@pytest.mark.django_db
def test_merge_persons_gives_the_others_explicit_sibling_to_the_person_once():
    josef, other = PersonFactory(), PersonFactory()
    franz, maria = PersonFactory(given_names="Franz"), PersonFactory(given_names="Maria")
    SiblingPairFactory(person_a=josef, person_b=franz)
    SiblingPairFactory(person_a=franz, person_b=other, gedcom_raw=[{"tag": "_UID", "value": "F7"}])
    SiblingPairFactory(person_a=maria, person_b=other)
    theresia = SiblingPairFactory(person_a=other, person_b=PersonFactory(given_names="Theresia")).person_b
    SiblingPairFactory(person_a=josef, person_b=other)

    merge_persons(person_id=josef.pk, other_id=other.pk, from_other=[])

    assert list(SiblingPair.objects.order_by("pk").values_list("person_a", "person_b", "gedcom_raw")) == [
        (josef.pk, franz.pk, [{"tag": "_UID", "value": "F7"}]),
        (maria.pk, josef.pk, []),
        (josef.pk, theresia.pk, []),
    ]


@pytest.mark.django_db
def test_merge_persons_drops_an_explicit_sibling_who_shares_a_parent_afterwards():
    josef, other, franz = PersonFactory(), PersonFactory(), PersonFactory(given_names="Franz")
    SiblingPairFactory(person_a=josef, person_b=franz)
    johann = PersonFactory(given_names="Johann")
    ParentChildFactory(parent=johann, child=other)
    ParentChildFactory(parent=johann, child=franz)

    merge_persons(person_id=josef.pk, other_id=other.pk, from_other=[])

    assert SiblingPair.objects.exists() is False


@pytest.mark.django_db
def test_merge_persons_drops_explicit_siblings_among_the_children_of_both():
    josef, other = PersonFactory(), PersonFactory()
    anna = ParentChildFactory(parent=josef).child
    franz = ParentChildFactory(parent=other).child
    SiblingPairFactory(person_a=anna, person_b=franz)

    merge_persons(person_id=josef.pk, other_id=other.pk, from_other=[])

    assert (SiblingPair.objects.exists(), ParentChild.objects.filter(parent=josef).count()) == (False, 2)


@pytest.mark.django_db
def test_merge_persons_makes_one_family_of_a_family_both_imports_brought_parents_first():
    paf_couple = PartnershipFactory()
    paf_child = ParentChildFactory(parent=paf_couple.person_a, partnership=paf_couple).child
    ParentChildFactory(parent=paf_couple.person_b, child=paf_child, partnership=paf_couple)
    myheritage_couple = PartnershipFactory()
    myheritage_child = ParentChildFactory(parent=myheritage_couple.person_a, partnership=myheritage_couple).child
    ParentChildFactory(parent=myheritage_couple.person_b, child=myheritage_child, partnership=myheritage_couple)

    merge_persons(person_id=paf_couple.person_a_id, other_id=myheritage_couple.person_a_id, from_other=[])
    merge_persons(person_id=paf_couple.person_b_id, other_id=myheritage_couple.person_b_id, from_other=[])
    merge_persons(person_id=paf_child.pk, other_id=myheritage_child.pk, from_other=[])

    assert (
        list(Partnership.objects.values_list("pk", flat=True)),
        set(ParentChild.objects.values_list("parent", "child", "partnership")),
    ) == (
        [paf_couple.pk],
        {
            (paf_couple.person_a_id, paf_child.pk, paf_couple.pk),
            (paf_couple.person_b_id, paf_child.pk, paf_couple.pk),
        },
    )


@pytest.mark.django_db
def test_merge_persons_refuses_the_same_person():
    josef = PersonFactory()

    with pytest.raises(ValidationError, match="nicht mit sich selbst"):
        merge_persons(person_id=josef.pk, other_id=josef.pk, from_other=[])


@pytest.mark.django_db
def test_merge_persons_refuses_a_couple():
    partnership = PartnershipFactory()

    with pytest.raises(ValidationError, match="ein Paar"):
        merge_persons(person_id=partnership.person_b_id, other_id=partnership.person_a_id, from_other=[])


@pytest.mark.parametrize("from_descendant", [True, False])
@pytest.mark.django_db
def test_merge_persons_refuses_an_ancestor_and_their_descendant(from_descendant):
    link = ParentChildFactory(child=ParentChildFactory().parent)
    grandparent, grandchild = link.parent, ParentChild.objects.exclude(pk=link.pk).get().child
    person, other = (grandchild, grandparent) if from_descendant else (grandparent, grandchild)

    with pytest.raises(ValidationError, match="Vorfahr und sein Nachkomme"):
        merge_persons(person_id=person.pk, other_id=other.pk, from_other=[])


@pytest.mark.django_db
def test_merge_persons_refuses_more_than_two_birth_parents_and_writes_nothing():
    josef, other = PersonFactory(), PersonFactory()
    ParentChildFactory(child=josef)
    ParentChildFactory(child=josef)
    ParentChildFactory(child=other)

    with pytest.raises(ValidationError, match=r"3 leibliche Eltern\. Führ zuerst die Eltern zusammen"):
        merge_persons(person_id=josef.pk, other_id=other.pk, from_other=[])

    assert Person.objects.filter(pk=other.pk).exists() is True


@pytest.mark.django_db
def test_merge_persons_refuses_somebody_not_in_the_tree():
    josef = PersonFactory()

    with pytest.raises(Person.DoesNotExist):
        merge_persons(person_id=josef.pk, other_id=josef.pk + 1, from_other=[])
