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
def test_partnerschaft_refuses_a_person_as_their_own_partner_on_save():
    josef = PersonFactory()

    with pytest.raises(ValidationError, match="Niemand ist sein eigener Partner"):
        PartnerschaftFactory(person_a=josef, person_b=josef)


@pytest.mark.django_db
def test_partnerschaft_refuses_a_person_as_their_own_partner_in_the_database():
    josef = PersonFactory()

    with pytest.raises(IntegrityError, match="partnerschaft_nicht_selbst"):
        Partnerschaft.objects.bulk_create([Partnerschaft(person_a=josef, person_b=josef)])


@pytest.mark.django_db
def test_partnerschaft_refuses_the_same_pair_the_other_way_round_on_save():
    partnerschaft = PartnerschaftFactory()

    with pytest.raises(ValidationError, match="Diese beiden sind schon ein Paar"):
        PartnerschaftFactory(person_a=partnerschaft.person_b, person_b=partnerschaft.person_a)


@pytest.mark.django_db
def test_partnerschaft_refuses_the_same_pair_the_other_way_round_in_the_database():
    partnerschaft = PartnerschaftFactory()

    with pytest.raises(IntegrityError, match="partnerschaft_einmal_pro_paar"):
        Partnerschaft.objects.bulk_create(
            [Partnerschaft(person_a=partnerschaft.person_b, person_b=partnerschaft.person_a)]
        )


@pytest.mark.django_db
def test_partnerschaft_refuses_an_unknown_kind_on_save():
    with pytest.raises(ValidationError, match="Ehe, eine Lebensgemeinschaft oder unbekannt"):
        PartnerschaftFactory(art="verlobt")


@pytest.mark.django_db
def test_partnerschaft_refuses_an_unknown_kind_in_the_database():
    josef, theresia = PersonFactory.create_batch(2)

    with pytest.raises(IntegrityError, match="partnerschaft_art_gueltig"):
        Partnerschaft.objects.bulk_create([Partnerschaft(person_a=josef, person_b=theresia, art="verlobt")])


@pytest.mark.django_db
def test_partnerschaft_enthaelt_both_partners():
    partnerschaft = PartnerschaftFactory()

    assert partnerschaft.enthaelt(person_id=partnerschaft.person_b_id) is True


@pytest.mark.django_db
def test_partnerschaft_enthaelt_nobody_else():
    partnerschaft = PartnerschaftFactory()

    assert partnerschaft.enthaelt(person_id=PersonFactory().pk) is False
