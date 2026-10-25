import pytest

from apps.family_tree.readers.gedcom_import import tree_is_empty
from apps.family_tree.tests.factories.person import PersonFactory


@pytest.mark.django_db
def test_tree_is_empty_without_anybody():
    assert tree_is_empty() is True


@pytest.mark.django_db
def test_tree_is_empty_not_once_somebody_is_in_it():
    PersonFactory()

    assert tree_is_empty() is False
