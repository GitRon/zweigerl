import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.family_tree.models import ParentChild
from apps.family_tree.tests.factories.parent_child import ParentChildFactory
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.sibling_pair import SiblingPairFactory


def test_parent_child_str_points_from_parent_to_child():
    parent_child = ParentChildFactory.build(
        parent=PersonFactory.build(given_names="Johann"), child=PersonFactory.build(given_names="Lena")
    )

    assert str(parent_child) == "Johann Huber → Lena Huber"


def test_parent_child_clean_leaves_a_link_without_parent_to_the_field_validation():
    parent_child = ParentChild(child=PersonFactory.build(pk=1))

    assert parent_child.clean() is None


@pytest.mark.django_db
def test_parent_child_clean_checks_the_partnership_before_the_child_is_saved():
    parent_child = ParentChild(parent=PersonFactory(), child=PersonFactory.build(), partnership=PartnershipFactory())

    with pytest.raises(ValidationError, match="gehört nicht zu dieser Partnerschaft"):
        parent_child.clean()


@pytest.mark.django_db
def test_parent_child_clean_accepts_a_parent_of_a_child_not_saved_yet():
    parent_child = ParentChild(parent=PersonFactory(), child=PersonFactory.build())

    assert parent_child.clean() is None


@pytest.mark.django_db
def test_parent_child_refuses_a_partnership_without_the_parent_on_save():
    with pytest.raises(ValidationError, match="gehört nicht zu dieser Partnerschaft"):
        ParentChildFactory(partnership=PartnershipFactory())


@pytest.mark.django_db
def test_parent_child_saves_with_the_partnership_of_the_parent():
    partnership = PartnershipFactory()

    parent_child = ParentChildFactory(parent=partnership.person_a, partnership=partnership)

    assert ParentChild.objects.get().partnership == parent_child.partnership


@pytest.mark.django_db
def test_parent_child_refuses_a_shared_parent_of_explicit_siblings():
    franz = PersonFactory()
    katharina, stefan = PersonFactory.create_batch(2)
    SiblingPairFactory(person_a=stefan, person_b=katharina)
    ParentChildFactory(parent=franz, child=stefan)

    with pytest.raises(ValidationError, match="Lösche erst diese Geschwister-Verbindung"):
        ParentChildFactory(parent=franz, child=katharina)


@pytest.mark.django_db
def test_parent_child_refuses_a_shared_parent_of_explicit_siblings_stored_the_other_way_round():
    franz = PersonFactory()
    katharina, stefan = PersonFactory.create_batch(2)
    SiblingPairFactory(person_a=katharina, person_b=stefan)
    ParentChildFactory(parent=franz, child=stefan)

    with pytest.raises(ValidationError, match="Lösche erst diese Geschwister-Verbindung"):
        ParentChildFactory(parent=franz, child=katharina)


@pytest.mark.django_db
def test_parent_child_refuses_a_third_birth_parent():
    lena = PersonFactory()
    ParentChildFactory.create_batch(2, child=lena)

    with pytest.raises(ValidationError, match="schon zwei leibliche Eltern"):
        ParentChildFactory(child=lena, pedigree=ParentChild.Pedigree.BIRTH)


@pytest.mark.django_db
def test_parent_child_accepts_an_adoptive_parent_beside_two_birth_parents():
    lena = PersonFactory()
    ParentChildFactory.create_batch(2, child=lena)

    ParentChildFactory(child=lena, pedigree=ParentChild.Pedigree.ADOPTED)

    assert ParentChild.objects.filter(child=lena).count() == 3


@pytest.mark.django_db
def test_parent_child_refuses_a_person_as_their_own_parent_on_save():
    johann = PersonFactory()

    with pytest.raises(ValidationError, match="Niemand ist sein eigener Elternteil"):
        ParentChildFactory(parent=johann, child=johann)


@pytest.mark.django_db
def test_parent_child_refuses_a_person_as_their_own_parent_in_the_database():
    johann = PersonFactory()

    with pytest.raises(IntegrityError, match="parentchild_not_self"):
        ParentChild.objects.bulk_create([ParentChild(parent=johann, child=johann)])


@pytest.mark.django_db
def test_parent_child_refuses_the_same_link_twice_on_save():
    parent_child = ParentChildFactory(pedigree=ParentChild.Pedigree.ADOPTED)

    with pytest.raises(ValidationError, match="Diese Eltern-Kind-Verbindung gibt es schon"):
        ParentChildFactory(parent=parent_child.parent, child=parent_child.child, pedigree=ParentChild.Pedigree.ADOPTED)


@pytest.mark.django_db
def test_parent_child_refuses_the_same_link_twice_in_the_database():
    parent_child = ParentChildFactory()

    with pytest.raises(IntegrityError, match=r"family_tree_parentchild\.parent_id, family_tree_parentchild\.child_id"):
        ParentChild.objects.bulk_create([ParentChild(parent=parent_child.parent, child=parent_child.child)])


@pytest.mark.django_db
def test_parent_child_refuses_an_unknown_pedigree_on_save():
    with pytest.raises(ValidationError, match="leiblich, adoptiert, Pflegekind oder unbekannt"):
        ParentChildFactory(pedigree="guessed")


@pytest.mark.django_db
def test_parent_child_refuses_an_unknown_pedigree_in_the_database():
    johann, lena = PersonFactory.create_batch(2)

    with pytest.raises(IntegrityError, match="parentchild_pedigree_valid"):
        ParentChild.objects.bulk_create([ParentChild(parent=johann, child=lena, pedigree="guessed")])
