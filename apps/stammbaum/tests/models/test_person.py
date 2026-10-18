import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.stammbaum.models import Person
from apps.stammbaum.tests.factories.person import PersonFactory


def test_person_str_joins_first_and_family_names():
    person = PersonFactory.build(vornamen="Anna Maria", familienname="Huber")

    assert str(person) == "Anna Maria Huber"


def test_person_str_without_a_name():
    person = PersonFactory.build(vornamen="", familienname="")

    assert str(person) == "Ohne Namen"


@pytest.mark.django_db
def test_person_starts_with_unknown_life_status_and_no_raw_gedcom():
    person = Person.objects.get(pk=PersonFactory().pk)

    assert (person.lebensstatus, person.gedcom_roh) == (Person.Lebensstatus.UNBEKANNT, [])


@pytest.mark.django_db
def test_person_refuses_an_unknown_sex_on_save():
    with pytest.raises(ValidationError, match="männlich, weiblich, divers oder unbekannt"):
        PersonFactory(geschlecht="Q")


@pytest.mark.django_db
def test_person_refuses_an_unknown_sex_in_the_database():
    with pytest.raises(IntegrityError, match="person_geschlecht_gueltig"):
        Person.objects.bulk_create([PersonFactory.build(geschlecht="Q")])


@pytest.mark.django_db
def test_person_refuses_an_unknown_life_status_on_save():
    with pytest.raises(ValidationError, match="lebend, verstorben oder unbekannt"):
        PersonFactory(lebensstatus="vielleicht")


@pytest.mark.django_db
def test_person_refuses_an_unknown_life_status_in_the_database():
    with pytest.raises(IntegrityError, match="person_lebensstatus_gueltig"):
        Person.objects.bulk_create([PersonFactory.build(lebensstatus="vielleicht")])
