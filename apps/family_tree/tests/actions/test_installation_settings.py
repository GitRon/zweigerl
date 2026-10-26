import pytest

from apps.family_tree.actions.backup import BackupRefusedError
from apps.family_tree.actions.installation_settings import set_backup_dir
from apps.family_tree.models import InstallationSettings
from apps.family_tree.tests.factories.installation_settings import InstallationSettingsFactory


@pytest.mark.django_db
def test_set_backup_dir_keeps_the_folder_as_an_absolute_path(tmp_path):
    set_backup_dir(backup_dir=f"  {tmp_path / 'backups' / '..'}  ")

    assert InstallationSettings.objects.get().backup_dir == str(tmp_path.resolve())


@pytest.mark.django_db
def test_set_backup_dir_clears_the_folder_when_empty(tmp_path):
    InstallationSettingsFactory(backup_dir=str(tmp_path))

    set_backup_dir(backup_dir=" ")

    assert InstallationSettings.objects.get().backup_dir == ""


@pytest.mark.django_db
def test_set_backup_dir_refuses_a_folder_a_backup_would_refuse(settings, tmp_path):
    settings.DATA_DIR = tmp_path

    with pytest.raises(BackupRefusedError, match="liegt im Datenordner"):
        set_backup_dir(backup_dir=str(tmp_path))

    assert InstallationSettings.objects.exists() is False
