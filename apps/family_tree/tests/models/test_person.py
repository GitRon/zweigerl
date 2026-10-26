import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.family_tree.models import Person
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.tree import TreeFactory


def test_person_str_joins_first_and_family_names():
    person = PersonFactory.build(given_names="Anna Maria", surname="Huber")

    assert str(person) == "Anna Maria Huber"


def test_person_str_without_a_name():
    person = PersonFactory.build(given_names="", surname="")

    assert str(person) == "Ohne Namen"


@pytest.mark.django_db
def test_person_starts_with_unknown_life_status_and_no_raw_gedcom():
    person = Person.objects.get(pk=PersonFactory().pk)

    assert (person.living_status, person.gedcom_raw) == (Person.LivingStatus.UNKNOWN, [])


@pytest.mark.django_db
def test_person_refuses_an_unknown_sex_on_save():
    with pytest.raises(ValidationError, match="männlich, weiblich, divers oder unbekannt"):
        PersonFactory(sex="Q")


@pytest.mark.django_db
def test_person_refuses_an_unknown_sex_in_the_database():
    with pytest.raises(IntegrityError, match="person_sex_valid"):
        Person.objects.bulk_create([PersonFactory.build(tree=TreeFactory(), sex="Q")])


@pytest.mark.django_db
def test_person_refuses_an_unknown_life_status_on_save():
    with pytest.raises(ValidationError, match="lebend, verstorben oder unbekannt"):
        PersonFactory(living_status="vielleicht")


@pytest.mark.django_db
def test_person_refuses_an_unknown_life_status_in_the_database():
    with pytest.raises(IntegrityError, match="person_living_status_valid"):
        Person.objects.bulk_create([PersonFactory.build(tree=TreeFactory(), living_status="vielleicht")])
