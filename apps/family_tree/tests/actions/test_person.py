import datetime

import pytest
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils import timezone

from apps.family_tree.actions.person import (
    Relation,
    add_relative,
    change_name_and_status,
    create_person,
    delete_person,
    link_relative,
    unlink_relative,
)
from apps.family_tree.models import Citation, Fact, ParentChild, Partnership, Person, SiblingPair, Source, TreeSettings
from apps.family_tree.tests.factories.citation import CitationFactory
from apps.family_tree.tests.factories.fact import FactFactory
from apps.family_tree.tests.factories.parent_child import ParentChildFactory
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.sibling_pair import SiblingPairFactory
from apps.family_tree.tests.factories.source import SourceFactory
from apps.family_tree.tests.factories.tree_settings import TreeSettingsFactory

FIELDS = {
    "given_names": "Rosa",
    "surname": "Huber",
    "sex": Person.Sex.FEMALE,
    "living_status": Person.LivingStatus.LIVING,
}


@pytest.mark.django_db
def test_create_person_saves_the_names_without_surrounding_spaces():
    person = create_person(**{**FIELDS, "given_names": "  Rosa ", "surname": " Huber"})

    assert Person.objects.values_list("given_names", "surname", "sex", "living_status").get(pk=person.pk) == (
        "Rosa",
        "Huber",
        "F",
        "living",
    )


@pytest.mark.django_db
def test_create_person_makes_the_first_person_the_home_person():
    person = create_person(**FIELDS)

    assert TreeSettings.objects.get().home_person == person


@pytest.mark.django_db
def test_create_person_leaves_the_home_person_of_a_tree_with_people():
    PersonFactory()

    create_person(**FIELDS)

    assert TreeSettings.objects.exists() is False


@pytest.mark.django_db
def test_create_person_refuses_a_sex_that_is_none():
    with pytest.raises(ValidationError, match="Das Geschlecht ist männlich, weiblich, divers oder unbekannt"):
        create_person(**{**FIELDS, "sex": "Q"})


@pytest.mark.django_db
def test_add_relative_adds_a_parent():
    lena = PersonFactory()

    mother = add_relative(person_id=lena.pk, relation=Relation.PARENT, **FIELDS)

    assert list(ParentChild.objects.values_list("parent", "child", "pedigree")) == [(mother.pk, lena.pk, "birth")]


@pytest.mark.django_db
def test_add_relative_adds_a_partner():
    lena = PersonFactory()

    partner = add_relative(person_id=lena.pk, relation=Relation.PARTNER, **FIELDS)

    assert list(Partnership.objects.values_list("person_a", "person_b", "kind")) == [(lena.pk, partner.pk, "unknown")]


@pytest.mark.django_db
def test_add_relative_adds_a_child():
    lena = PersonFactory()

    child = add_relative(person_id=lena.pk, relation=Relation.CHILD, **FIELDS)

    assert list(ParentChild.objects.values_list("parent", "child")) == [(lena.pk, child.pk)]


@pytest.mark.django_db
def test_add_relative_gives_a_sibling_the_same_parents():
    couple = PartnershipFactory()
    lena = PersonFactory()
    ParentChildFactory(parent=couple.person_a, child=lena, partnership=couple)
    ParentChildFactory(parent=couple.person_b, child=lena, partnership=couple, pedigree=ParentChild.Pedigree.ADOPTED)

    sister = add_relative(person_id=lena.pk, relation=Relation.SIBLING, **FIELDS)

    assert set(ParentChild.objects.filter(child=sister).values_list("parent", "partnership", "pedigree")) == {
        (couple.person_a.pk, couple.pk, "birth"),
        (couple.person_b.pk, couple.pk, "adopted"),
    }


@pytest.mark.django_db
def test_add_relative_stores_a_sibling_without_known_parents_as_a_pair():
    lena = PersonFactory()

    sister = add_relative(person_id=lena.pk, relation=Relation.SIBLING, **FIELDS)

    assert list(SiblingPair.objects.values_list("person_a", "person_b")) == [(lena.pk, sister.pk)]


@pytest.mark.django_db
def test_add_relative_refuses_somebody_not_in_the_tree():
    lena = PersonFactory()

    with pytest.raises(Person.DoesNotExist, match="Person matching query does not exist"):
        add_relative(person_id=lena.pk + 1, relation=Relation.CHILD, **FIELDS)


@pytest.mark.django_db
def test_add_relative_refuses_a_relation_that_is_none():
    lena = PersonFactory()

    with pytest.raises(ValueError, match="'cousin' is not a valid Relation"):
        add_relative(person_id=lena.pk, relation="cousin", **FIELDS)


@pytest.mark.django_db
def test_add_relative_saves_nothing_when_a_rule_refuses_the_link():
    lena = PersonFactory()
    ParentChildFactory.create_batch(2, child=lena)

    with pytest.raises(ValidationError, match="Dieses Kind hat schon zwei leibliche Eltern"):
        add_relative(person_id=lena.pk, relation=Relation.PARENT, **FIELDS)

    assert Person.objects.count() == 3


@pytest.mark.django_db
def test_add_relative_adds_a_child_of_the_couple():
    couple = PartnershipFactory()

    child = add_relative(person_id=couple.person_a.pk, relation=Relation.CHILD, partnership_id=couple.pk, **FIELDS)

    assert set(ParentChild.objects.filter(child=child).values_list("parent", "partnership")) == {
        (couple.person_a.pk, couple.pk),
        (couple.person_b.pk, couple.pk),
    }


@pytest.mark.django_db
def test_add_relative_pairs_a_second_parent_with_the_first():
    mother = ParentChildFactory()

    father = add_relative(person_id=mother.child.pk, relation=Relation.PARENT, pair_with_parent=True, **FIELDS)

    couple = Partnership.objects.get()
    assert (couple.person_a, couple.person_b) == (mother.parent, father)
    assert set(ParentChild.objects.values_list("parent", "partnership")) == {
        (mother.parent.pk, couple.pk),
        (father.pk, couple.pk),
    }


@pytest.mark.django_db
def test_add_relative_leaves_a_second_parent_without_a_couple_when_not_asked_to():
    mother = ParentChildFactory()

    add_relative(person_id=mother.child.pk, relation=Relation.PARENT, **FIELDS)

    assert list(ParentChild.objects.values_list("partnership", flat=True)) == [None, None]


@pytest.mark.django_db
def test_link_relative_links_somebody_in_the_tree_as_parent():
    lena, josef = PersonFactory.create_batch(2)

    linked = link_relative(person_id=lena.pk, relation=Relation.PARENT, relative_id=josef.pk)

    assert linked == josef
    assert list(ParentChild.objects.values_list("parent", "child", "partnership")) == [(josef.pk, lena.pk, None)]


@pytest.mark.django_db
def test_link_relative_puts_a_parent_with_the_couple_they_already_are():
    couple = PartnershipFactory()
    mother = ParentChildFactory(parent=couple.person_a)

    link_relative(person_id=mother.child.pk, relation=Relation.PARENT, relative_id=couple.person_b.pk)

    assert set(ParentChild.objects.values_list("parent", "partnership")) == {
        (couple.person_a.pk, couple.pk),
        (couple.person_b.pk, couple.pk),
    }


@pytest.mark.django_db
def test_link_relative_keeps_the_couple_the_first_parents_link_already_names():
    earlier = PartnershipFactory()
    mother = ParentChildFactory(parent=earlier.person_a, partnership=earlier)
    father = PersonFactory()

    link_relative(person_id=mother.child.pk, relation=Relation.PARENT, relative_id=father.pk, pair_with_parent=True)

    couple = Partnership.objects.exclude(pk=earlier.pk).get()
    assert set(ParentChild.objects.values_list("parent", "partnership")) == {
        (earlier.person_a.pk, earlier.pk),
        (father.pk, couple.pk),
    }


@pytest.mark.django_db
def test_link_relative_links_somebody_in_the_tree_as_partner():
    lena, stefan = PersonFactory.create_batch(2)

    link_relative(person_id=lena.pk, relation=Relation.PARTNER, relative_id=stefan.pk)

    assert list(Partnership.objects.values_list("person_a", "person_b")) == [(lena.pk, stefan.pk)]


@pytest.mark.django_db
def test_link_relative_gives_the_other_parents_link_the_couple():
    couple = PartnershipFactory()
    stepchild = ParentChildFactory(parent=couple.person_b)

    link_relative(
        person_id=couple.person_a.pk, relation=Relation.CHILD, relative_id=stepchild.child.pk, partnership_id=couple.pk
    )

    assert set(ParentChild.objects.values_list("parent", "partnership")) == {
        (couple.person_a.pk, couple.pk),
        (couple.person_b.pk, couple.pk),
    }


@pytest.mark.django_db
def test_link_relative_leaves_the_other_parents_link_with_its_own_couple():
    couple = PartnershipFactory()
    earlier = PartnershipFactory(person_a=couple.person_b)
    stepchild = ParentChildFactory(parent=couple.person_b, partnership=earlier)

    link_relative(
        person_id=couple.person_a.pk, relation=Relation.CHILD, relative_id=stepchild.child.pk, partnership_id=couple.pk
    )

    assert ParentChild.objects.get(pk=stepchild.pk).partnership == earlier


@pytest.mark.django_db
def test_link_relative_refuses_a_couple_the_person_is_not_part_of():
    lena, child = PersonFactory.create_batch(2)
    others = PartnershipFactory()

    with pytest.raises(ValidationError, match="Der Elternteil gehört nicht zu dieser Partnerschaft"):
        link_relative(person_id=lena.pk, relation=Relation.CHILD, relative_id=child.pk, partnership_id=others.pk)


@pytest.mark.django_db
def test_link_relative_gives_a_sibling_the_persons_parents():
    mother = ParentChildFactory()
    sister = PersonFactory()

    link_relative(person_id=mother.child.pk, relation=Relation.SIBLING, relative_id=sister.pk)

    assert list(ParentChild.objects.filter(child=sister).values_list("parent", flat=True)) == [mother.parent.pk]


@pytest.mark.django_db
def test_link_relative_gives_the_person_the_siblings_parents_while_theirs_are_unknown():
    lena = PersonFactory()
    mother = ParentChildFactory()

    link_relative(person_id=lena.pk, relation=Relation.SIBLING, relative_id=mother.child.pk)

    assert list(ParentChild.objects.filter(child=lena).values_list("parent", flat=True)) == [mother.parent.pk]


@pytest.mark.django_db
def test_link_relative_stores_siblings_without_known_parents_as_a_pair():
    lena, sister = PersonFactory.create_batch(2)

    link_relative(person_id=lena.pk, relation=Relation.SIBLING, relative_id=sister.pk)

    assert list(SiblingPair.objects.values_list("person_a", "person_b")) == [(lena.pk, sister.pk)]


@pytest.mark.django_db
def test_link_relative_refuses_siblings_through_a_shared_parent():
    lena = ParentChildFactory()
    sister = ParentChildFactory(parent=lena.parent)

    with pytest.raises(ValidationError, match="sind darüber schon Geschwister"):
        link_relative(person_id=lena.child.pk, relation=Relation.SIBLING, relative_id=sister.child.pk)


@pytest.mark.django_db
def test_link_relative_refuses_the_person_themself():
    lena = PersonFactory()

    with pytest.raises(ValidationError, match="Niemand ist sein eigener Verwandter"):
        link_relative(person_id=lena.pk, relation=Relation.PARTNER, relative_id=lena.pk)


@pytest.mark.django_db
def test_link_relative_refuses_a_descendant_as_parent():
    child = ParentChildFactory()
    grandchild = ParentChildFactory(parent=child.child)

    with pytest.raises(ValidationError, match="Niemand ist sein eigener Vorfahr"):
        link_relative(person_id=child.parent.pk, relation=Relation.PARENT, relative_id=grandchild.child.pk)

    assert ParentChild.objects.count() == 2


@pytest.mark.django_db
def test_link_relative_refuses_a_link_already_there():
    mother = ParentChildFactory()

    with pytest.raises(ValidationError, match="Diese Eltern-Kind-Verbindung gibt es schon"):
        link_relative(person_id=mother.parent.pk, relation=Relation.CHILD, relative_id=mother.child.pk)


@pytest.mark.django_db
def test_link_relative_refuses_somebody_not_in_the_tree():
    lena = PersonFactory()

    with pytest.raises(Person.DoesNotExist, match="Person matching query does not exist"):
        link_relative(person_id=lena.pk, relation=Relation.PARENT, relative_id=lena.pk + 1)


ALIVE = {"sex": Person.Sex.FEMALE, "living_status": Person.LivingStatus.LIVING, "death_year": None}


@pytest.mark.django_db
def test_change_name_and_status_corrects_the_names_and_sex():
    gerti = PersonFactory(given_names="Gertrud", surname="Hubr")

    changed = change_name_and_status(
        person_id=gerti.pk,
        given_names=" Gertrud Maria ",
        surname="Huber",
        call_name="Gerti",
        **ALIVE,
    )

    gerti.refresh_from_db()
    assert (changed, gerti.given_names, gerti.surname, gerti.call_name, gerti.sex) == (
        gerti,
        "Gertrud Maria",
        "Huber",
        "Gerti",
        Person.Sex.FEMALE,
    )


@pytest.mark.django_db
def test_change_name_and_status_records_the_death_year_as_a_death_fact():
    johann = PersonFactory(given_names="Johann", living_status=Person.LivingStatus.LIVING)

    change_name_and_status(
        person_id=johann.pk,
        given_names="Johann",
        surname="Huber",
        call_name="",
        sex=Person.Sex.MALE,
        living_status=Person.LivingStatus.DECEASED,
        death_year=2009,
    )

    assert list(johann.facts.values_list("kind", "date_kind", "date_1", "precision", "reliability")) == [
        (Fact.Kind.DEATH, "exact", datetime.date(2009, 1, 1), "year", Fact.Reliability.DOCUMENTED)
    ]


@pytest.mark.django_db
def test_change_name_and_status_without_a_death_year_records_no_death_fact():
    johann = PersonFactory(given_names="Johann")

    change_name_and_status(
        person_id=johann.pk,
        given_names="Johann",
        surname="Huber",
        call_name="",
        **{**ALIVE, "living_status": Person.LivingStatus.DECEASED},
    )

    johann.refresh_from_db()
    assert (johann.living_status, johann.facts.exists()) == (Person.LivingStatus.DECEASED, False)


@pytest.mark.django_db
def test_change_name_and_status_keeps_a_death_fact_already_recorded():
    death = FactFactory(kind=Fact.Kind.DEATH, date_1=datetime.date(2009, 5, 2))

    change_name_and_status(
        person_id=death.person.pk,
        given_names="Johann",
        surname="Huber",
        call_name="",
        sex=Person.Sex.MALE,
        living_status=Person.LivingStatus.DECEASED,
        death_year=2010,
    )

    assert list(Fact.objects.all()) == [death]


@pytest.mark.django_db
def test_change_name_and_status_ignores_a_death_year_for_somebody_alive():
    lena = PersonFactory(given_names="Lena")

    change_name_and_status(
        person_id=lena.pk, given_names="Lena", surname="Huber", call_name="", **{**ALIVE, "death_year": 2009}
    )

    assert lena.facts.exists() is False


@pytest.mark.django_db
def test_change_name_and_status_refuses_a_death_year_in_the_future():
    johann = PersonFactory(given_names="Johann", surname="Huber")

    with pytest.raises(ValidationError, match="Das Sterbejahr ist eine Jahreszahl, höchstens die heurige"):
        change_name_and_status(
            person_id=johann.pk,
            given_names="Hans",
            surname="Huber",
            call_name="",
            sex=Person.Sex.MALE,
            living_status=Person.LivingStatus.DECEASED,
            death_year=timezone.localdate().year + 1,
        )

    johann.refresh_from_db()
    assert (johann.given_names, johann.facts.exists()) == ("Johann", False)


@pytest.mark.django_db
def test_change_name_and_status_refuses_a_sex_the_person_cannot_have():
    lena = PersonFactory(given_names="Lena")

    with pytest.raises(ValidationError, match="ist keine gültige Option"):
        change_name_and_status(
            person_id=lena.pk, given_names="Lena", surname="Huber", call_name="", **{**ALIVE, "sex": "Z"}
        )


@pytest.mark.django_db
def test_change_name_and_status_refuses_somebody_not_in_the_tree():
    lena = PersonFactory()

    with pytest.raises(Person.DoesNotExist, match="Person matching query does not exist"):
        change_name_and_status(person_id=lena.pk + 1, given_names="", surname="", call_name="", **ALIVE)


@pytest.mark.django_db
def test_delete_person_takes_their_facts_and_citations_and_keeps_sources_and_relatives():
    johann = PersonFactory(given_names="Johann")
    marriage = PartnershipFactory(person_a=johann)
    child_link = ParentChildFactory(parent=johann)
    CitationFactory(fact=FactFactory(person=johann))
    CitationFactory(fact=FactFactory(person=None, partnership=marriage, kind=Fact.Kind.MARRIAGE))
    SourceFactory(people=[johann])

    delete_person(person_id=johann.pk)

    assert (
        Person.objects.filter(pk=johann.pk).exists(),
        Fact.objects.exists(),
        Citation.objects.exists(),
        Partnership.objects.exists(),
        Source.objects.count(),
        set(Person.objects.values_list("pk", flat=True)),
    ) == (False, False, False, False, 3, {marriage.person_b_id, child_link.child_id})


@pytest.mark.django_db
def test_delete_person_refuses_the_home_person():
    lena = TreeSettingsFactory().home_person

    with pytest.raises(ValidationError, match="Das ist die Ausgangsperson"):
        delete_person(person_id=lena.pk)
    assert Person.objects.filter(pk=lena.pk).exists() is True


@pytest.mark.django_db
def test_delete_person_of_somebody_not_there_raises():
    with pytest.raises(Person.DoesNotExist, match="Person matching query does not exist"):
        delete_person(person_id=404)


@pytest.mark.django_db
@pytest.mark.parametrize(("relation", "of_child"), [(Relation.PARENT, True), (Relation.CHILD, False)])
def test_unlink_relative_removes_the_one_parent_link(relation, of_child):
    link = ParentChildFactory()
    other = ParentChildFactory(child=link.child)
    person, relative = (link.child, link.parent) if of_child else (link.parent, link.child)

    unlink_relative(person_id=person.pk, relation=relation, relative_id=relative.pk)

    assert list(ParentChild.objects.all()) == [other]


@pytest.mark.django_db
def test_unlink_relative_removes_a_partnership_from_either_side_with_its_facts_and_keeps_the_children():
    partnership = PartnershipFactory()
    FactFactory(person=None, partnership=partnership, kind=Fact.Kind.MARRIAGE)
    child_link = ParentChildFactory(parent=partnership.person_a, partnership=partnership)

    unlink_relative(person_id=partnership.person_b_id, relation=Relation.PARTNER, relative_id=partnership.person_a_id)

    child_link.refresh_from_db()
    assert (Partnership.objects.exists(), Fact.objects.exists(), child_link.partnership) == (False, False, None)


@pytest.mark.django_db
def test_unlink_relative_removes_an_explicit_sibling_pair():
    pair = SiblingPairFactory()

    unlink_relative(person_id=pair.person_b_id, relation=Relation.SIBLING, relative_id=pair.person_a_id)

    assert SiblingPair.objects.exists() is False


@pytest.mark.django_db
def test_unlink_relative_without_such_a_link_raises():
    # Siblings through a shared parent: the link is the parent's.
    link = ParentChildFactory()
    sibling = ParentChildFactory(parent=link.parent)

    with pytest.raises(ObjectDoesNotExist, match="Keine solche Verbindung"):
        unlink_relative(person_id=link.child_id, relation=Relation.SIBLING, relative_id=sibling.child_id)


@pytest.mark.django_db
def test_unlink_relative_refuses_an_unknown_relation():
    link = ParentChildFactory()

    with pytest.raises(ValueError, match="'cousin' is not a valid Relation"):
        unlink_relative(person_id=link.child_id, relation="cousin", relative_id=link.parent_id)
