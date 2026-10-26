import datetime
from unittest import mock

import pytest

from apps.family_tree.domain.backup import BackupAge
from apps.family_tree.readers.backup import BackupFolder, backup_folder, last_backup
from apps.family_tree.tests.factories.installation_settings import InstallationSettingsFactory


@pytest.mark.django_db
def test_last_backup_without_settings_is_never():
    assert last_backup() == BackupAge(text="noch nie", overdue=True)


@pytest.mark.django_db
@mock.patch("apps.family_tree.readers.backup.localdate", return_value=datetime.date(2026, 10, 20))
def test_last_backup_counts_from_the_local_day_of_the_backup(_localdate, settings):
    settings.TIME_ZONE = "Europe/Vienna"
    # Late on the 18th in UTC is already the 19th in Vienna.
    InstallationSettingsFactory(last_backup_at=datetime.datetime(2026, 10, 18, 23, 30, tzinfo=datetime.UTC))

    assert last_backup() == BackupAge(text="gestern", overdue=False)


@pytest.mark.django_db
def test_backup_folder_without_settings_is_empty():
    assert backup_folder() == BackupFolder(path="", free="")


@pytest.mark.django_db
@mock.patch("apps.family_tree.readers.backup.disk_usage", return_value=mock.Mock(free=48_250_000_000))
def test_backup_folder_says_how_much_space_is_left(_disk_usage, tmp_path):
    InstallationSettingsFactory(backup_dir=str(tmp_path))

    assert backup_folder() == BackupFolder(path=str(tmp_path), free="48,2 GB")


@pytest.mark.django_db
def test_backup_folder_that_cannot_be_reached_has_no_free_space(tmp_path):
    InstallationSettingsFactory(backup_dir=str(tmp_path / "unplugged-disk"))

    assert backup_folder() == BackupFolder(path=str(tmp_path / "unplugged-disk"), free="")
