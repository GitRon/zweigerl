import pytest
from django.urls import reverse

from apps.family_tree.models import Note
from apps.family_tree.tests.factories.note import NoteFactory
from apps.family_tree.tests.factories.person import PersonFactory


def _post(client, url: str, data: dict) -> str:
    response = client.post(url, data, headers={"Datastar-Request": "true"})

    return b"".join(response.streaming_content).decode()


def _get(client, url: str):
    return client.get(url, headers={"Datastar-Request": "true"})


@pytest.mark.django_db
def test_note_create_view_writes_the_note_signed_by_the_user_and_patches_the_list(admin_client, admin_user):
    lena = PersonFactory()

    body = _post(admin_client, reverse("family_tree:note-create-view", kwargs={"pk": lena.pk}), {"text": "Fragen"})

    assert list(Note.objects.values_list("author", "text")) == [(admin_user.pk, "Fragen")]
    assert (
        "data: mode replace" in body,
        'id="person-card-note-list"' in body,
        'id="person-card-note-count"' in body,
        "Passt. Die Notiz steht da." in body,
    ) == (True, True, True, True)


@pytest.mark.django_db
def test_note_create_view_refuses_somebody_not_in_the_tree(admin_client):
    body = _post(admin_client, reverse("family_tree:note-create-view", kwargs={"pk": 404}), {"text": "Fragen"})

    assert "Diese Person ist nicht mehr im Baum." in body


@pytest.mark.django_db
def test_note_create_view_refuses_a_note_without_text(admin_client):
    lena = PersonFactory()

    body = _post(admin_client, reverse("family_tree:note-create-view", kwargs={"pk": lena.pk}), {"text": " "})

    assert "Eine Notiz braucht einen Text." in body


@pytest.mark.django_db
def test_note_change_view_saves_the_text_and_patches_the_list(admin_client):
    note = NoteFactory(text="Zwei Jahre?")

    body = _post(
        admin_client,
        reverse("family_tree:note-change-view", kwargs={"pk": note.person.pk, "note_pk": note.pk}),
        {"text": "Drei Jahre."},
    )

    note.refresh_from_db()
    assert note.text == "Drei Jahre."
    assert ('id="person-card-note-list"' in body, "Passt. Die Notiz ist geändert." in body) == (True, True)


@pytest.mark.django_db
def test_note_change_view_of_a_note_no_longer_there_says_so(admin_client):
    body = _post(
        admin_client,
        reverse("family_tree:note-change-view", kwargs={"pk": PersonFactory().pk, "note_pk": 404}),
        {"text": "Drei Jahre."},
    )

    assert "Diese Notiz ist nicht mehr da." in body


@pytest.mark.django_db
def test_note_change_view_refuses_an_emptied_text(admin_client):
    note = NoteFactory()

    body = _post(
        admin_client,
        reverse("family_tree:note-change-view", kwargs={"pk": note.person.pk, "note_pk": note.pk}),
        {"text": ""},
    )

    assert "Eine Notiz braucht einen Text." in body


@pytest.mark.django_db
def test_delete_note_view_asks_first_in_a_dialog(admin_client):
    note = NoteFactory()

    body = b"".join(
        _get(
            admin_client,
            reverse("family_tree:delete-note-view", kwargs={"pk": note.person.pk, "note_pk": note.pk}),
        ).streaming_content
    ).decode()

    assert ("selector body" in body, "mode append" in body, 'id="delete-note-dialog"' in body) == (True, True, True)


@pytest.mark.django_db
def test_delete_note_view_asks_about_a_note_not_there_not_at_all(admin_client):
    response = _get(
        admin_client, reverse("family_tree:delete-note-view", kwargs={"pk": PersonFactory().pk, "note_pk": 404})
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_delete_note_view_deletes_it_closes_the_dialog_and_patches_the_list(admin_client):
    note = NoteFactory()

    body = _post(
        admin_client, reverse("family_tree:delete-note-view", kwargs={"pk": note.person.pk, "note_pk": note.pk}), {}
    )

    assert Note.objects.exists() is False
    assert (
        "selector #delete-note-dialog" in body,
        'id="person-card-note-list"' in body,
        "Passt. Die Notiz ist gelöscht." in body,
    ) == (True, True, True)


@pytest.mark.django_db
def test_delete_note_view_of_a_note_no_longer_there_says_so(admin_client):
    body = _post(
        admin_client, reverse("family_tree:delete-note-view", kwargs={"pk": PersonFactory().pk, "note_pk": 404}), {}
    )

    assert "Diese Notiz ist nicht mehr da." in body
