import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.family_tree.models import Partnership
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.person import PersonFactory


def test_partnership_str_names_both():
    partnership = PartnershipFactory.build(
        person_a=PersonFactory.build(given_names="Josef"), person_b=PersonFactory.build(given_names="Theresia")
    )

    assert str(partnership) == "Josef Huber & Theresia Huber"


@pytest.mark.django_db
def test_partnership_refuses_a_person_as_their_own_partner_on_save():
    josef = PersonFactory()

    with pytest.raises(ValidationError, match="Niemand ist sein eigener Partner"):
        PartnershipFactory(person_a=josef, person_b=josef)


@pytest.mark.django_db
def test_partnership_refuses_a_person_as_their_own_partner_in_the_database():
    josef = PersonFactory()

    with pytest.raises(IntegrityError, match="partnership_not_self"):
        Partnership.objects.bulk_create([Partnership(person_a=josef, person_b=josef)])


@pytest.mark.django_db
def test_partnership_refuses_the_same_pair_the_other_way_round_on_save():
    partnership = PartnershipFactory()

    with pytest.raises(ValidationError, match="Diese beiden sind schon ein Paar"):
        PartnershipFactory(person_a=partnership.person_b, person_b=partnership.person_a)


@pytest.mark.django_db
def test_partnership_refuses_the_same_pair_the_other_way_round_in_the_database():
    partnership = PartnershipFactory()

    with pytest.raises(IntegrityError, match="partnership_once_per_pair"):
        Partnership.objects.bulk_create([Partnership(person_a=partnership.person_b, person_b=partnership.person_a)])


@pytest.mark.django_db
def test_partnership_refuses_an_unknown_kind_on_save():
    with pytest.raises(ValidationError, match="Ehe, eine Lebensgemeinschaft oder unbekannt"):
        PartnershipFactory(kind="engaged")


@pytest.mark.django_db
def test_partnership_refuses_an_unknown_kind_in_the_database():
    josef, theresia = PersonFactory.create_batch(2)

    with pytest.raises(IntegrityError, match="partnership_kind_valid"):
        Partnership.objects.bulk_create([Partnership(person_a=josef, person_b=theresia, kind="engaged")])


@pytest.mark.django_db
def test_partnership_includes_both_partners():
    partnership = PartnershipFactory()

    assert partnership.includes(person_id=partnership.person_b_id) is True


@pytest.mark.django_db
def test_partnership_includes_nobody_else():
    partnership = PartnershipFactory()

    assert partnership.includes(person_id=PersonFactory().pk) is False


@pytest.mark.django_db
def test_partnership_refuses_partners_of_two_trees():
    lena = PersonFactory()

    with pytest.raises(ValidationError, match="Die beiden gehören zu verschiedenen Stammbäumen"):
        PartnershipFactory(person_a=lena, person_b=PersonFactory(tree__name="Familie Berger"))
