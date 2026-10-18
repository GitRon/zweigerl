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
def test_geschwister_clean_refuses_a_person_as_their_own_sibling():
    katharina = PersonFactory()

    with pytest.raises(ValidationError, match="Niemand ist sein eigenes Geschwister"):
        Geschwister(person_a=katharina, person_b=katharina).clean()


@pytest.mark.django_db
def test_geschwister_clean_refuses_siblings_who_share_a_known_parent():
    franz = PersonFactory()
    katharina, stefan = PersonFactory.create_batch(2)
    ElternKindFactory(elternteil=franz, kind=katharina)
    ElternKindFactory(elternteil=franz, kind=stefan)

    with pytest.raises(ValidationError, match="gemeinsamen Elternteil"):
        Geschwister(person_a=katharina, person_b=stefan).clean()


@pytest.mark.django_db
def test_geschwister_clean_accepts_siblings_without_a_known_parent():
    katharina, stefan = PersonFactory.create_batch(2)
    ElternKindFactory(kind=katharina)
    ElternKindFactory(kind=stefan)

    assert Geschwister(person_a=stefan, person_b=katharina).clean() is None


@pytest.mark.django_db
def test_geschwister_is_stored_once_per_pair_whichever_way_round():
    geschwister = GeschwisterFactory()

    with pytest.raises(IntegrityError, match="UNIQUE constraint failed"):
        GeschwisterFactory(person_a=geschwister.person_b, person_b=geschwister.person_a)
