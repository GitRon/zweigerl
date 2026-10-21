import datetime
import sqlite3
from contextlib import closing
from pathlib import Path
from unittest import mock

import pytest

from apps.family_tree.actions.backup import BackupRefusedError, check_backup_dir, create_backup
from apps.family_tree.models import TreeSettings
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.tree_settings import TreeSettingsFactory

MOMENT = datetime.datetime(2026, 10, 19, 14, 30, 12, tzinfo=datetime.UTC)
GEDCOM = "0 HEAD\n0 TRLR\n"


@pytest.fixture
def media_root(settings, tmp_path) -> Path:
    settings.MEDIA_ROOT = tmp_path / "data" / "media"
    settings.MEDIA_ROOT.mkdir(parents=True)
    return settings.MEDIA_ROOT


@pytest.fixture
def backup_dir(tmp_path) -> Path:
    path = tmp_path / "backups"
    path.mkdir()
    return path


@pytest.mark.django_db(transaction=True)
@mock.patch("apps.family_tree.actions.backup.localtime", return_value=MOMENT)
def test_create_backup_writes_database_dump_gedcom_and_media(_localtime, media_root, backup_dir):
    backup = create_backup(gedcom=GEDCOM, target=backup_dir)

    assert sorted(path.name for path in backup.path.iterdir()) == [
        "media",
        "zweigerl.ged",
        "zweigerl.sql",
        "zweigerl.sqlite3",
    ]


@pytest.mark.django_db(transaction=True)
@mock.patch("apps.family_tree.actions.backup.localtime", return_value=MOMENT)
def test_create_backup_names_the_folder_after_the_moment(_localtime, media_root, backup_dir):
    backup = create_backup(gedcom=GEDCOM, target=backup_dir)

    assert backup.path == backup_dir.resolve() / "2026-10-19_143012"


@pytest.mark.django_db(transaction=True)
def test_create_backup_leaves_no_incomplete_folder_behind(media_root, backup_dir):
    create_backup(gedcom=GEDCOM, target=backup_dir)

    assert list(backup_dir.glob("*.incomplete")) == []


@pytest.mark.django_db(transaction=True)
def test_create_backup_copies_the_database(media_root, backup_dir):
    PersonFactory(given_names="Lena", surname="Huber")

    backup = create_backup(gedcom=GEDCOM, target=backup_dir)

    with closing(sqlite3.connect(backup.path / "zweigerl.sqlite3")) as copy:
        assert copy.execute("SELECT given_names FROM family_tree_person").fetchall() == [("Lena",)]


@pytest.mark.django_db(transaction=True)
def test_create_backup_dumps_the_copy_as_sql(media_root, backup_dir):
    PersonFactory(given_names="Lena", surname="Huber")

    backup = create_backup(gedcom=GEDCOM, target=backup_dir)

    assert "'Lena'" in (backup.path / "zweigerl.sql").read_text(encoding="utf-8")


@pytest.mark.django_db(transaction=True)
def test_create_backup_writes_the_gedcom_it_was_given(media_root, backup_dir):
    backup = create_backup(gedcom="0 HEAD\n1 NOTE Gößl\n0 TRLR\n", target=backup_dir)

    assert (backup.path / "zweigerl.ged").read_text(encoding="utf-8") == "0 HEAD\n1 NOTE Gößl\n0 TRLR\n"


@pytest.mark.django_db(transaction=True)
def test_create_backup_copies_the_media(media_root, backup_dir):
    (media_root / "photos" / "17").mkdir(parents=True)
    (media_root / "photos" / "17" / "original.jpg").write_bytes(b"jpeg")

    backup = create_backup(gedcom=GEDCOM, target=backup_dir)

    assert (backup.path / "media" / "photos" / "17" / "original.jpg").read_bytes() == b"jpeg"


@pytest.mark.django_db(transaction=True)
def test_create_backup_writes_an_empty_media_folder_without_media(settings, tmp_path, backup_dir):
    settings.MEDIA_ROOT = tmp_path / "nothing-uploaded-yet"

    backup = create_backup(gedcom=GEDCOM, target=backup_dir)

    assert list((backup.path / "media").iterdir()) == []


@pytest.mark.django_db(transaction=True)
def test_create_backup_counts_people_files_and_bytes(media_root, backup_dir):
    PersonFactory.create_batch(2)
    (media_root / "sources" / "3").mkdir(parents=True)
    (media_root / "sources" / "3" / "7.pdf").write_bytes(b"%PDF")

    backup = create_backup(gedcom=GEDCOM, target=backup_dir)

    written = (
        (backup.path / "zweigerl.sqlite3").stat().st_size
        + (backup.path / "zweigerl.sql").stat().st_size
        + len(GEDCOM)
        + len(b"%PDF")
    )
    assert (backup.people, backup.files, backup.size) == (2, 1, written)


@pytest.mark.django_db(transaction=True)
def test_create_backup_names_what_an_earlier_run_left_incomplete(media_root, backup_dir):
    leftover = backup_dir / "2026-10-18_090000.incomplete"
    leftover.mkdir()

    backup = create_backup(gedcom=GEDCOM, target=backup_dir)

    assert backup.incomplete == [leftover.resolve()]


@pytest.mark.django_db(transaction=True)
@mock.patch("apps.family_tree.actions.backup.localtime", return_value=MOMENT)
def test_create_backup_remembers_the_moment_of_the_backup(_localtime, media_root, backup_dir):
    create_backup(gedcom=GEDCOM, target=backup_dir)

    assert TreeSettings.objects.get().last_backup_at == MOMENT


@pytest.mark.django_db(transaction=True)
def test_create_backup_goes_to_the_folder_of_the_settings(media_root, backup_dir):
    TreeSettingsFactory(backup_dir=str(backup_dir))

    backup = create_backup(gedcom=GEDCOM)

    assert backup.path.parent == backup_dir.resolve()


@pytest.mark.django_db
def test_create_backup_refuses_without_a_folder():
    with pytest.raises(BackupRefusedError, match="noch kein Sicherungsordner eingestellt"):
        create_backup(gedcom=GEDCOM)


@pytest.mark.django_db
def test_create_backup_refuses_a_folder_that_does_not_exist(tmp_path):
    with pytest.raises(BackupRefusedError, match="gibt es nicht"):
        create_backup(gedcom=GEDCOM, target=tmp_path / "unplugged-disk")


@pytest.mark.django_db
def test_create_backup_refuses_a_folder_inside_the_data_directory(settings, tmp_path):
    settings.DATA_DIR = tmp_path
    (tmp_path / "backups").mkdir()

    with pytest.raises(BackupRefusedError, match="liegt im Datenordner"):
        create_backup(gedcom=GEDCOM, target=tmp_path / "backups")


@pytest.mark.django_db
def test_create_backup_refuses_a_folder_inside_the_repository(settings, tmp_path):
    settings.BASE_DIR = tmp_path

    with pytest.raises(BackupRefusedError, match="liegt im Repository"):
        create_backup(gedcom=GEDCOM, target=tmp_path)


@pytest.mark.django_db
@mock.patch("apps.family_tree.actions.backup.access", return_value=False)
def test_create_backup_refuses_a_folder_it_cannot_write(_access, backup_dir):
    with pytest.raises(BackupRefusedError, match="darf Zweigerl nicht schreiben"):
        create_backup(gedcom=GEDCOM, target=backup_dir)


@pytest.mark.django_db
@mock.patch("apps.family_tree.actions.backup.localtime", return_value=MOMENT)
def test_create_backup_refuses_a_second_backup_of_the_same_moment(_localtime, backup_dir):
    (backup_dir / "2026-10-19_143012").mkdir()

    with pytest.raises(BackupRefusedError, match="schon eine Sicherung 2026-10-19_143012"):
        create_backup(gedcom=GEDCOM, target=backup_dir)


def test_check_backup_dir_makes_the_folder_absolute(backup_dir, monkeypatch):
    monkeypatch.chdir(backup_dir.parent)

    assert check_backup_dir(path=Path("backups")) == backup_dir.resolve()
