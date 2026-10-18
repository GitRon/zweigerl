import datetime

import pytest

from apps.family_tree.models import Fact, Person
from apps.family_tree.readers.person import PersonList, PersonListEntry, Relatives, person_list, relatives
from apps.family_tree.tests.factories.fact import FactFactory
from apps.family_tree.tests.factories.parent_child import ParentChildFactory
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.sibling_pair import SiblingPairFactory


@pytest.mark.django_db
def test_relatives_finds_parents_partner_and_children():
    johann = PersonFactory(given_names="Johann")
    maria = PersonFactory(given_names="Maria")
    lena = PersonFactory(given_names="Lena")
    markus = PersonFactory(given_names="Markus")
    emma = PersonFactory(given_names="Emma")
    PersonFactory(given_names="Fremd")
    ParentChildFactory(parent=johann, child=lena)
    ParentChildFactory(parent=maria, child=lena)
    PartnershipFactory(person_a=markus, person_b=lena)
    ParentChildFactory(parent=lena, child=emma)

    result = relatives(person=lena)

    assert result == Relatives(parents=[johann, maria], partners=[markus], children=[emma], siblings=[])


@pytest.mark.django_db
def test_relatives_finds_partners_on_either_side_of_the_pair():
    lena = PersonFactory(given_names="Lena")
    markus = PersonFactory(given_names="Markus")
    anton = PersonFactory(given_names="Anton")
    PartnershipFactory(person_a=lena, person_b=markus)
    PartnershipFactory(person_a=anton, person_b=lena)

    assert relatives(person=lena).partners == [anton, markus]


@pytest.mark.django_db
def test_relatives_derives_siblings_from_a_shared_parent_and_half_siblings_too():
    johann = PersonFactory(given_names="Johann")
    maria = PersonFactory(given_names="Maria")
    lena = PersonFactory(given_names="Lena")
    lukas = PersonFactory(given_names="Lukas")
    florian = PersonFactory(given_names="Florian")
    PersonFactory(given_names="Fremd")
    ParentChildFactory(parent=johann, child=lena)
    ParentChildFactory(parent=maria, child=lena)
    ParentChildFactory(parent=johann, child=lukas)
    ParentChildFactory(parent=maria, child=lukas)
    ParentChildFactory(parent=johann, child=florian)

    assert relatives(person=lena).siblings == [florian, lukas]


@pytest.mark.django_db
def test_relatives_adds_explicit_siblings_from_either_side():
    katharina = PersonFactory(given_names="Katharina")
    stefan = PersonFactory(given_names="Stefan")
    anna = PersonFactory(given_names="Anna")
    PersonFactory(given_names="Fremd")
    SiblingPairFactory(person_a=katharina, person_b=stefan)
    SiblingPairFactory(person_a=anna, person_b=katharina)

    assert relatives(person=katharina).siblings == [anna, stefan]


@pytest.mark.django_db
def test_person_list_sorts_by_family_name_and_counts_everybody():
    zach = PersonFactory(given_names="Anna", surname="Zach")
    oehler = PersonFactory(given_names="Anna", surname="Öhler")

    result = person_list(search="")

    assert (result.entries[0].person, result.entries[1].person, result.total) == (oehler, zach, 2)


@pytest.mark.django_db
def test_person_list_keeps_only_who_matches_the_search():
    lena = PersonFactory(given_names="Lena", surname="Huber")
    PersonFactory(given_names="Markus", surname="Brandl")

    result = person_list(search="hub")

    assert result == PersonList(
        entries=[PersonListEntry(person=lena, name="Lena Huber", initials="LH", lifespan="—")], total=2
    )


@pytest.mark.django_db
def test_person_list_finds_the_call_name():
    gertrud = PersonFactory(given_names="Gertrud", surname="Huber", call_name="Gerti")
    PersonFactory(given_names="Gerhard", surname="Huber")

    result = person_list(search="gerti")

    assert result.entries == [PersonListEntry(person=gertrud, name="Gerti Huber", initials="GH", lifespan="—")]


@pytest.mark.django_db
def test_person_list_shows_the_earliest_birth_and_death():
    josef = PersonFactory(given_names="Josef", living_status=Person.LivingStatus.DECEASED)
    FactFactory(person=josef, date_1=datetime.date(1931, 3, 12))
    FactFactory(person=josef, date_1=datetime.date(1932, 1, 1), reliability=Fact.Reliability.HANDED_DOWN)
    FactFactory(person=josef, kind=Fact.Kind.DEATH, date_1=datetime.date(2009, 5, 1))
    FactFactory(person=josef, kind=Fact.Kind.BAPTISM, date_1=datetime.date(1930, 1, 1))

    assert person_list(search="").entries[0].lifespan == "1931 – 2009"


@pytest.mark.django_db
def test_person_list_leaves_the_end_open_for_somebody_not_known_to_be_dead():
    lena = PersonFactory(given_names="Lena", living_status=Person.LivingStatus.LIVING)
    FactFactory(person=lena, date_1=datetime.date(1989, 3, 12))

    assert person_list(search="").entries[0].lifespan == "1989 –"


@pytest.mark.django_db
def test_person_list_asks_for_the_death_date_of_somebody_dead():
    theresia = PersonFactory(given_names="Theresia", living_status=Person.LivingStatus.DECEASED)
    FactFactory(person=theresia, date_1=datetime.date(1934, 1, 1))

    assert person_list(search="").entries[0].lifespan == "1934 – ?"
