import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError

from apps.family_tree.models import TreeSettings
from apps.family_tree.tests.factories.tree_settings import TreeSettingsFactory


def test_tree_settings_str():
    assert str(TreeSettings()) == "Einstellungen des Stammbaums"


@pytest.mark.django_db
def test_tree_settings_refuses_a_second_row_on_save():
    with pytest.raises(ValidationError, match="Es gibt nur eine Zeile Einstellungen"):
        TreeSettings(id=2).save()


@pytest.mark.django_db
def test_tree_settings_refuses_a_second_row_in_the_database():
    with pytest.raises(IntegrityError, match="treesettings_single_row"):
        TreeSettings.objects.bulk_create([TreeSettings(id=2)])


@pytest.mark.django_db
def test_tree_settings_protects_the_home_person_from_deletion():
    tree_settings = TreeSettingsFactory()

    with pytest.raises(ProtectedError, match="protected foreign keys"):
        tree_settings.home_person.delete()
