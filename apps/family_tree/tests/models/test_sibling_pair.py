import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.family_tree.models import SiblingPair
from apps.family_tree.tests.factories.parent_child import ParentChildFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.sibling_pair import SiblingPairFactory


def test_sibling_pair_str_names_both():
    siblings = SiblingPairFactory.build(
        person_a=PersonFactory.build(given_names="Katharina"), person_b=PersonFactory.build(given_names="Stefan")
    )

    assert str(siblings) == "Katharina Huber & Stefan Huber"


def test_sibling_pair_clean_leaves_an_incomplete_pair_to_the_field_validation():
    siblings = SiblingPair(person_a=PersonFactory.build(pk=1))

    assert siblings.clean() is None


@pytest.mark.django_db
def test_sibling_pair_refuses_siblings_who_share_a_known_parent():
    franz = PersonFactory()
    katharina, stefan = PersonFactory.create_batch(2)
    ParentChildFactory(parent=franz, child=katharina)
    ParentChildFactory(parent=franz, child=stefan)

    with pytest.raises(ValidationError, match="gemeinsamen Elternteil"):
        SiblingPairFactory(person_a=katharina, person_b=stefan)


@pytest.mark.django_db
def test_sibling_pair_saves_siblings_without_a_known_shared_parent():
    katharina, stefan = PersonFactory.create_batch(2)
    ParentChildFactory(child=katharina)
    ParentChildFactory(child=stefan)

    SiblingPairFactory(person_a=stefan, person_b=katharina)

    assert SiblingPair.objects.count() == 1


@pytest.mark.django_db
def test_sibling_pair_refuses_a_person_as_their_own_sibling_on_save():
    katharina = PersonFactory()

    with pytest.raises(ValidationError, match="Niemand ist sein eigenes Geschwister"):
        SiblingPairFactory(person_a=katharina, person_b=katharina)


@pytest.mark.django_db
def test_sibling_pair_refuses_a_person_as_their_own_sibling_in_the_database():
    katharina = PersonFactory()

    with pytest.raises(IntegrityError, match="siblingpair_not_self"):
        SiblingPair.objects.bulk_create([SiblingPair(person_a=katharina, person_b=katharina)])


@pytest.mark.django_db
def test_sibling_pair_refuses_the_same_pair_the_other_way_round_on_save():
    siblings = SiblingPairFactory()

    with pytest.raises(ValidationError, match="schon als Geschwister eingetragen"):
        SiblingPairFactory(person_a=siblings.person_b, person_b=siblings.person_a)


@pytest.mark.django_db
def test_sibling_pair_refuses_the_same_pair_the_other_way_round_in_the_database():
    siblings = SiblingPairFactory()

    with pytest.raises(IntegrityError, match="siblingpair_once_per_pair"):
        SiblingPair.objects.bulk_create([SiblingPair(person_a=siblings.person_b, person_b=siblings.person_a)])


@pytest.mark.django_db
def test_sibling_pair_refuses_siblings_of_two_trees():
    lena = PersonFactory()

    with pytest.raises(ValidationError, match="Die beiden gehören zu verschiedenen Stammbäumen"):
        SiblingPairFactory(person_a=lena, person_b=PersonFactory(tree__name="Familie Berger"))
