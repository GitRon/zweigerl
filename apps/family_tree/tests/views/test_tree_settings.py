import datetime
from unittest import mock

import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from apps.family_tree.models import TreeSettings
from apps.family_tree.readers.backup import BackupFolder
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.tree_settings import TreeSettingsFactory


@pytest.mark.django_db
def test_tree_settings_view_renders_the_settings_page(admin_client):
    response = admin_client.get(reverse("family_tree:tree-settings-view"))

    assert response.status_code == 200
    assertTemplateUsed(response, "family_tree/tree_settings.html")


@pytest.mark.django_db
def test_tree_settings_view_shows_the_home_person(admin_client):
    tree_settings = TreeSettingsFactory()

    response = admin_client.get(reverse("family_tree:tree-settings-view"))

    assert response.context["home_person"] == tree_settings.home_person


@pytest.mark.django_db
def test_tree_settings_view_shows_the_backup_folder(admin_client, tmp_path):
    TreeSettingsFactory(backup_dir=str(tmp_path / "unplugged-disk"))

    response = admin_client.get(reverse("family_tree:tree-settings-view"))

    assert response.context["backup_folder"] == BackupFolder(path=str(tmp_path / "unplugged-disk"), free="")


@pytest.mark.django_db
def test_home_person_view_saves_the_choice_and_confirms_it(admin_client):
    markus = PersonFactory(given_names="Markus", surname="Brandl")

    response = admin_client.post(
        reverse("family_tree:home-person-view"), {"home_person": markus.pk}, headers={"Datastar-Request": "true"}
    )

    body = b"".join(response.streaming_content).decode()
    assert TreeSettings.objects.get().home_person == markus
    assert "Passt. Markus Brandl ist jetzt die Ausgangsperson." in body


@pytest.mark.django_db
def test_home_person_view_patches_who_hangs_loose_now(admin_client):
    lena = PersonFactory(given_names="Lena", surname="Huber")
    markus = PersonFactory(given_names="Markus", surname="Brandl")
    TreeSettingsFactory(home_person=lena)

    response = admin_client.post(
        reverse("family_tree:home-person-view"), {"home_person": markus.pk}, headers={"Datastar-Request": "true"}
    )

    events = b"".join(response.streaming_content).decode().split("\n\n")
    assert "Lena Huber" in next(event for event in events if 'id="loose-people"' in event)


@pytest.mark.django_db
@pytest.mark.parametrize("home_person", ["", "kein-schlüssel", "999"])
def test_home_person_view_refuses_somebody_not_in_the_tree(admin_client, home_person):
    response = admin_client.post(
        reverse("family_tree:home-person-view"), {"home_person": home_person}, headers={"Datastar-Request": "true"}
    )

    body = b"".join(response.streaming_content).decode()
    assert TreeSettings.objects.exists() is False
    assert "Diese Person ist nicht mehr im Baum." in body


@pytest.mark.django_db
def test_backup_dir_view_saves_the_folder_and_patches_the_section(admin_client, tmp_path):
    response = admin_client.post(
        reverse("family_tree:backup-dir-view"), {"backup_dir": str(tmp_path)}, headers={"Datastar-Request": "true"}
    )

    body = b"".join(response.streaming_content).decode()
    assert TreeSettings.objects.get().backup_dir == str(tmp_path.resolve())
    assert ('id="backup"' in body, "Passt. Der Sicherungsordner ist gespeichert." in body) == (True, True)


@pytest.mark.django_db
def test_backup_dir_view_refuses_a_folder_a_backup_would_refuse(admin_client, tmp_path):
    response = admin_client.post(
        reverse("family_tree:backup-dir-view"),
        {"backup_dir": str(tmp_path / "unplugged-disk")},
        headers={"Datastar-Request": "true"},
    )

    body = b"".join(response.streaming_content).decode()
    assert TreeSettings.objects.exists() is False
    assert "gibt es nicht" in body


@pytest.mark.django_db(transaction=True)
@mock.patch(
    "apps.family_tree.actions.backup.localtime",
    return_value=datetime.datetime(2026, 10, 19, 14, 30, 12, tzinfo=datetime.UTC),
)
def test_backup_view_says_where_the_backup_went_and_patches_the_last_backup(
    _localtime, admin_client, settings, tmp_path
):
    settings.MEDIA_ROOT = tmp_path / "media"
    (tmp_path / "backups").mkdir()
    TreeSettingsFactory(backup_dir=str(tmp_path / "backups"))

    response = admin_client.post(reverse("family_tree:backup-view"), headers={"Datastar-Request": "true"})

    body = b"".join(response.streaming_content).decode()
    assert (
        'id="backup-status"' in body,
        f"Gesichert in {tmp_path.resolve() / 'backups' / '2026-10-19_143012'} (" in body,
    ) == (
        True,
        True,
    )


@pytest.mark.django_db(transaction=True)
def test_backup_view_names_what_an_earlier_run_left_incomplete(admin_client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    leftover = tmp_path / "2026-10-18_090000.incomplete"
    leftover.mkdir()
    TreeSettingsFactory(backup_dir=str(tmp_path))

    response = admin_client.post(reverse("family_tree:backup-view"), headers={"Datastar-Request": "true"})

    assert f"Unvollständig liegen geblieben: {leftover.resolve()}" in b"".join(response.streaming_content).decode()


@pytest.mark.django_db
def test_backup_view_turns_a_refusal_into_a_toast(admin_client):
    response = admin_client.post(reverse("family_tree:backup-view"), headers={"Datastar-Request": "true"})

    assert "noch kein Sicherungsordner eingestellt" in b"".join(response.streaming_content).decode()
