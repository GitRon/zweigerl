import pytest

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
