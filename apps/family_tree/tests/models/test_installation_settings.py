import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.family_tree.models import InstallationSettings


def test_installation_settings_str():
    assert str(InstallationSettings()) == "Einstellungen der Installation"


@pytest.mark.django_db
def test_installation_settings_refuses_a_second_row_on_save():
    with pytest.raises(ValidationError, match="Es gibt nur eine Zeile Einstellungen"):
        InstallationSettings(id=2).save()


@pytest.mark.django_db
def test_installation_settings_refuses_a_second_row_in_the_database():
    with pytest.raises(IntegrityError, match="installationsettings_single_row"):
        InstallationSettings.objects.bulk_create([InstallationSettings(id=2)])
