import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.stammbaum.models import Partnerschaft
from apps.stammbaum.tests.factories.partnerschaft import PartnerschaftFactory
from apps.stammbaum.tests.factories.person import PersonFactory


def test_partnerschaft_str_names_both():
    partnerschaft = PartnerschaftFactory.build(
        person_a=PersonFactory.build(vornamen="Josef"), person_b=PersonFactory.build(vornamen="Theresia")
    )

    assert str(partnerschaft) == "Josef Huber & Theresia Huber"


@pytest.mark.django_db
def test_partnerschaft_clean_refuses_a_person_as_their_own_partner():
    josef = PersonFactory()

    with pytest.raises(ValidationError, match="Niemand ist sein eigener Partner"):
        Partnerschaft(person_a=josef, person_b=josef).clean()


@pytest.mark.django_db
def test_partnerschaft_full_clean_accepts_a_pair_entered_the_other_way_round():
    josef, theresia = PersonFactory.create_batch(2)
    partnerschaft = Partnerschaft(person_a=theresia, person_b=josef)

    partnerschaft.full_clean()

    assert (partnerschaft.person_a, partnerschaft.person_b) == (josef, theresia)


@pytest.mark.django_db
def test_partnerschaft_save_stores_the_lower_primary_key_first():
    josef, theresia = PersonFactory.create_batch(2)

    partnerschaft = PartnerschaftFactory(person_a=theresia, person_b=josef)

    assert (partnerschaft.person_a, partnerschaft.person_b) == (josef, theresia)


@pytest.mark.django_db
def test_partnerschaft_is_stored_once_per_pair():
    josef, theresia = PersonFactory.create_batch(2)
    PartnerschaftFactory(person_a=josef, person_b=theresia)

    with pytest.raises(IntegrityError, match="UNIQUE constraint failed: stammbaum_partnerschaft"):
        PartnerschaftFactory(person_a=theresia, person_b=josef)


@pytest.mark.django_db
def test_partnerschaft_enthaelt_both_partners():
    partnerschaft = PartnerschaftFactory()

    assert partnerschaft.enthaelt(person_id=partnerschaft.person_b_id) is True


@pytest.mark.django_db
def test_partnerschaft_enthaelt_nobody_else():
    partnerschaft = PartnerschaftFactory()

    assert partnerschaft.enthaelt(person_id=PersonFactory().pk) is False
