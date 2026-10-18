import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.stammbaum.models import Geschwister
from apps.stammbaum.tests.factories.eltern_kind import ElternKindFactory
from apps.stammbaum.tests.factories.geschwister import GeschwisterFactory
from apps.stammbaum.tests.factories.person import PersonFactory


def test_geschwister_str_names_both():
    geschwister = GeschwisterFactory.build(
        person_a=PersonFactory.build(vornamen="Katharina"), person_b=PersonFactory.build(vornamen="Stefan")
    )

    assert str(geschwister) == "Katharina Huber & Stefan Huber"


def test_geschwister_clean_leaves_an_incomplete_pair_to_the_field_validation():
    geschwister = Geschwister(person_a=PersonFactory.build(pk=1))

    assert geschwister.clean() is None


@pytest.mark.django_db
def test_geschwister_refuses_siblings_who_share_a_known_parent():
    franz = PersonFactory()
    katharina, stefan = PersonFactory.create_batch(2)
    ElternKindFactory(elternteil=franz, kind=katharina)
    ElternKindFactory(elternteil=franz, kind=stefan)

    with pytest.raises(ValidationError, match="gemeinsamen Elternteil"):
        GeschwisterFactory(person_a=katharina, person_b=stefan)


@pytest.mark.django_db
def test_geschwister_saves_siblings_without_a_known_shared_parent():
    katharina, stefan = PersonFactory.create_batch(2)
    ElternKindFactory(kind=katharina)
    ElternKindFactory(kind=stefan)

    GeschwisterFactory(person_a=stefan, person_b=katharina)

    assert Geschwister.objects.count() == 1


@pytest.mark.django_db
def test_geschwister_refuses_a_person_as_their_own_sibling_on_save():
    katharina = PersonFactory()

    with pytest.raises(ValidationError, match="Niemand ist sein eigenes Geschwister"):
        GeschwisterFactory(person_a=katharina, person_b=katharina)


@pytest.mark.django_db
def test_geschwister_refuses_a_person_as_their_own_sibling_in_the_database():
    katharina = PersonFactory()

    with pytest.raises(IntegrityError, match="geschwister_nicht_selbst"):
        Geschwister.objects.bulk_create([Geschwister(person_a=katharina, person_b=katharina)])


@pytest.mark.django_db
def test_geschwister_refuses_the_same_pair_the_other_way_round_on_save():
    geschwister = GeschwisterFactory()

    with pytest.raises(ValidationError, match="schon als Geschwister eingetragen"):
        GeschwisterFactory(person_a=geschwister.person_b, person_b=geschwister.person_a)


@pytest.mark.django_db
def test_geschwister_refuses_the_same_pair_the_other_way_round_in_the_database():
    geschwister = GeschwisterFactory()

    with pytest.raises(IntegrityError, match="geschwister_einmal_pro_paar"):
        Geschwister.objects.bulk_create([Geschwister(person_a=geschwister.person_b, person_b=geschwister.person_a)])
