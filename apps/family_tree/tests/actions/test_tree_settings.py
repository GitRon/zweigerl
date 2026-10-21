import pytest

from apps.family_tree.actions.backup import BackupRefusedError
from apps.family_tree.actions.tree_settings import choose_home_person, set_backup_dir
from apps.family_tree.models import Person, TreeSettings
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.tree_settings import TreeSettingsFactory


@pytest.mark.django_db
def test_choose_home_person_creates_the_settings():
    lena = PersonFactory()

    tree_settings = choose_home_person(person_id=lena.pk)

    assert TreeSettings.objects.get().home_person == tree_settings.home_person == lena


@pytest.mark.django_db
def test_choose_home_person_replaces_the_one_chosen_before():
    TreeSettingsFactory()
    markus = PersonFactory()

    choose_home_person(person_id=markus.pk)

    assert list(TreeSettings.objects.values_list("home_person", flat=True)) == [markus.pk]


@pytest.mark.django_db
def test_choose_home_person_refuses_somebody_not_in_the_tree():
    lena = PersonFactory()

    with pytest.raises(Person.DoesNotExist, match="Person matching query does not exist"):
        choose_home_person(person_id=lena.pk + 1)


@pytest.mark.django_db
def test_set_backup_dir_keeps_the_folder_as_an_absolute_path(tmp_path):
    set_backup_dir(backup_dir=f"  {tmp_path / 'backups' / '..'}  ")

    assert TreeSettings.objects.get().backup_dir == str(tmp_path.resolve())


@pytest.mark.django_db
def test_set_backup_dir_clears_the_folder_when_empty(tmp_path):
    TreeSettingsFactory(backup_dir=str(tmp_path))

    set_backup_dir(backup_dir=" ")

    assert TreeSettings.objects.get().backup_dir == ""


@pytest.mark.django_db
def test_set_backup_dir_refuses_a_folder_a_backup_would_refuse(settings, tmp_path):
    settings.DATA_DIR = tmp_path

    with pytest.raises(BackupRefusedError, match="liegt im Datenordner"):
        set_backup_dir(backup_dir=str(tmp_path))

    assert TreeSettings.objects.exists() is False
