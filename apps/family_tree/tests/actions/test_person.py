import datetime

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.family_tree.actions.person import change_name_and_status
from apps.family_tree.models import Fact, Person
from apps.family_tree.tests.factories.fact import FactFactory
from apps.family_tree.tests.factories.person import PersonFactory

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
