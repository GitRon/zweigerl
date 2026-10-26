import pytest

from apps.family_tree.readers.gedcom_import import tree_is_empty
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.tree import TreeFactory


@pytest.mark.django_db
def test_tree_is_empty_without_anybody():
    assert tree_is_empty(tree_id=TreeFactory().pk) is True


@pytest.mark.django_db
def test_tree_is_empty_while_only_another_tree_has_people():
    PersonFactory(tree__name="Familie Berger")

    assert tree_is_empty(tree_id=TreeFactory().pk) is True


@pytest.mark.django_db
def test_tree_is_empty_not_once_somebody_is_in_it():
    PersonFactory()

    assert tree_is_empty(tree_id=TreeFactory().pk) is False
