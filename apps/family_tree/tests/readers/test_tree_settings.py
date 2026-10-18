import pytest

from apps.family_tree.readers.tree_settings import home_person
from apps.family_tree.tests.factories.tree_settings import TreeSettingsFactory


@pytest.mark.django_db
def test_home_person_without_settings_is_none():
    assert home_person() is None


@pytest.mark.django_db
def test_home_person_is_the_chosen_person():
    tree_settings = TreeSettingsFactory()

    assert home_person() == tree_settings.home_person
