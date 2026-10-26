import datetime
from unittest import mock

import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from apps.family_tree.models import InstallationSettings, Tree
from apps.family_tree.readers.backup import BackupFolder
from apps.family_tree.tests.factories.installation_settings import InstallationSettingsFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.tree import TreeFactory


def _settings_url(*, tree: Tree) -> str:
    return reverse("family_tree:tree-settings-view", kwargs={"tree_pk": tree.pk})


@pytest.mark.django_db
def test_tree_settings_view_renders_the_settings_page(admin_client):
    tree = TreeFactory()

    response = admin_client.get(_settings_url(tree=tree))

    assert response.status_code == 200
    assertTemplateUsed(response, "family_tree/tree_settings.html")


@pytest.mark.django_db
def test_tree_settings_view_refuses_a_tree_that_is_not_there(admin_client):
    tree = TreeFactory()

    response = admin_client.get(reverse("family_tree:tree-settings-view", kwargs={"tree_pk": tree.pk + 1}))

    assert response.status_code == 404


@pytest.mark.django_db
def test_tree_settings_view_shows_the_home_person(admin_client):
    lena = TreeFactory(home_person=PersonFactory()).home_person

    response = admin_client.get(_settings_url(tree=lena.tree))

    assert response.context["home_person"] == lena


@pytest.mark.django_db
def test_tree_settings_view_says_whether_a_file_can_be_imported(admin_client):
    person = PersonFactory()

    response = admin_client.get(_settings_url(tree=person.tree))

    assert response.context["tree_empty"] is False


@pytest.mark.django_db
def test_tree_settings_view_shows_the_backup_folder(admin_client, tmp_path):
    InstallationSettingsFactory(backup_dir=str(tmp_path / "unplugged-disk"))

    response = admin_client.get(_settings_url(tree=TreeFactory()))

    assert response.context["backup_folder"] == BackupFolder(path=str(tmp_path / "unplugged-disk"), free="")


@pytest.mark.django_db
def test_home_person_view_saves_the_choice_and_confirms_it(admin_client):
    markus = PersonFactory(given_names="Markus", surname="Brandl")

    response = admin_client.post(
        reverse("family_tree:home-person-view", kwargs={"tree_pk": markus.tree_id}),
        {"home_person": markus.pk},
        headers={"Datastar-Request": "true"},
    )

    body = b"".join(response.streaming_content).decode()
    assert Tree.objects.get().home_person == markus
    assert "Passt. Markus Brandl ist jetzt die Ausgangsperson." in body


@pytest.mark.django_db
def test_home_person_view_patches_who_hangs_loose_now(admin_client):
    lena = PersonFactory(given_names="Lena", surname="Huber")
    markus = PersonFactory(given_names="Markus", surname="Brandl")
    TreeFactory(home_person=lena)

    response = admin_client.post(
        reverse("family_tree:home-person-view", kwargs={"tree_pk": lena.tree_id}),
        {"home_person": markus.pk},
        headers={"Datastar-Request": "true"},
    )

    events = b"".join(response.streaming_content).decode().split("\n\n")
    assert "Lena Huber" in next(event for event in events if 'id="loose-people"' in event)


@pytest.mark.django_db
@pytest.mark.parametrize("home_person", ["", "kein-schlüssel", "999"])
def test_home_person_view_refuses_somebody_not_in_the_tree(admin_client, home_person):
    tree = TreeFactory()

    response = admin_client.post(
        reverse("family_tree:home-person-view", kwargs={"tree_pk": tree.pk}),
        {"home_person": home_person},
        headers={"Datastar-Request": "true"},
    )

    body = b"".join(response.streaming_content).decode()
    assert Tree.objects.get().home_person is None
    assert "Diese Person ist nicht mehr im Baum." in body


@pytest.mark.django_db
def test_backup_dir_view_saves_the_folder_and_patches_the_section(admin_client, tmp_path):
    response = admin_client.post(
        reverse("family_tree:backup-dir-view", kwargs={"tree_pk": TreeFactory().pk}),
        {"backup_dir": str(tmp_path)},
        headers={"Datastar-Request": "true"},
    )

    body = b"".join(response.streaming_content).decode()
    assert InstallationSettings.objects.get().backup_dir == str(tmp_path.resolve())
    assert ('id="backup"' in body, "Passt. Der Sicherungsordner ist gespeichert." in body) == (True, True)


@pytest.mark.django_db
def test_backup_dir_view_refuses_a_folder_a_backup_would_refuse(admin_client, tmp_path):
    response = admin_client.post(
        reverse("family_tree:backup-dir-view", kwargs={"tree_pk": TreeFactory().pk}),
        {"backup_dir": str(tmp_path / "unplugged-disk")},
        headers={"Datastar-Request": "true"},
    )

    body = b"".join(response.streaming_content).decode()
    assert InstallationSettings.objects.exists() is False
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
    InstallationSettingsFactory(backup_dir=str(tmp_path / "backups"))
    tree = TreeFactory()

    response = admin_client.post(
        reverse("family_tree:backup-view", kwargs={"tree_pk": tree.pk}), headers={"Datastar-Request": "true"}
    )

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
    InstallationSettingsFactory(backup_dir=str(tmp_path))
    tree = TreeFactory()

    response = admin_client.post(
        reverse("family_tree:backup-view", kwargs={"tree_pk": tree.pk}), headers={"Datastar-Request": "true"}
    )

    assert f"Unvollständig liegen geblieben: {leftover.resolve()}" in b"".join(response.streaming_content).decode()


@pytest.mark.django_db
def test_backup_view_turns_a_refusal_into_a_toast(admin_client):
    tree = TreeFactory()

    response = admin_client.post(
        reverse("family_tree:backup-view", kwargs={"tree_pk": tree.pk}), headers={"Datastar-Request": "true"}
    )

    assert "noch kein Sicherungsordner eingestellt" in b"".join(response.streaming_content).decode()
