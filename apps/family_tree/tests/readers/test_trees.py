import pytest

from apps.family_tree.readers.trees import OpenTree, first_tree_id, home_person, open_tree, tree_id_by_name
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.tree import TreeFactory


@pytest.mark.django_db
def test_open_tree_is_the_tree_with_the_others_beside_it():
    berger = TreeFactory(name="Familie Berger")
    huber = TreeFactory(name="Familie Huber")
    auer = TreeFactory(name="Familie Auer")

    assert open_tree(pk=huber.pk) == OpenTree(tree=huber, others=[auer, berger])


@pytest.mark.django_db
def test_open_tree_of_a_tree_that_is_not_there_is_none():
    tree = TreeFactory()

    assert open_tree(pk=tree.pk + 1) is None


@pytest.mark.django_db
def test_first_tree_id_is_the_first_by_name():
    TreeFactory(name="Familie Huber")
    auer = TreeFactory(name="Familie Auer")

    assert first_tree_id() == auer.pk


@pytest.mark.django_db
def test_first_tree_id_without_a_tree_is_none():
    assert first_tree_id() is None


@pytest.mark.django_db
def test_home_person_while_nobody_is_chosen_is_none():
    assert home_person(tree_id=TreeFactory().pk) is None


@pytest.mark.django_db
def test_home_person_is_the_person_chosen_for_the_tree():
    lena = TreeFactory(home_person=PersonFactory()).home_person
    TreeFactory(name="Familie Berger", home_person=PersonFactory(tree__name="Familie Berger"))

    assert home_person(tree_id=lena.tree_id) == lena


@pytest.mark.django_db
def test_tree_id_by_name_finds_the_tree():
    TreeFactory(name="Familie Berger")
    huber = TreeFactory(name="Familie Huber")

    assert tree_id_by_name(name="Familie Huber") == huber.pk


@pytest.mark.django_db
def test_tree_id_by_name_without_such_a_tree_is_none():
    TreeFactory(name="Familie Huber")

    assert tree_id_by_name(name="Familie Berger") is None
