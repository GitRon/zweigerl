import pytest
from django.core.exceptions import ValidationError

from apps.family_tree.actions.person import Relation, add_relative, create_person
from apps.family_tree.models import ParentChild, Partnership, Person, SiblingPair, TreeSettings
from apps.family_tree.tests.factories.parent_child import ParentChildFactory
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.person import PersonFactory

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
