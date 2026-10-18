import io
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.family_tree.models import Photo, PhotoPerson
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.photo import PhotoFactory
from apps.family_tree.tests.factories.photo_person import PhotoPersonFactory
from apps.family_tree.tests.factories.tree_settings import TreeSettingsFactory


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path) -> Path:
    settings.MEDIA_ROOT = tmp_path

    return tmp_path


def _jpeg() -> SimpleUploadedFile:
    output = io.BytesIO()
    Image.new("RGB", (6, 8), "white").save(output, "JPEG")

    return SimpleUploadedFile("am Hof.jpg", output.getvalue())


def _post(client, url: str, data: dict) -> str:
    response = client.post(url, data, headers={"Datastar-Request": "true"})

    return b"".join(response.streaming_content).decode()


@pytest.mark.django_db
def test_photo_create_view_adds_the_photo_and_patches_tab_head_list_and_tree(admin_client):
    lena = PersonFactory()

    body = _post(admin_client, reverse("family_tree:photo-create-view", kwargs={"pk": lena.pk}), {"files": [_jpeg()]})

    assert list(PhotoPerson.objects.values_list("person", flat=True)) == [lena.pk]
    assert (
        "data: mode replace" in body,
        'id="person-card-photo-list"' in body,
        'id="person-card-photo-count"' in body,
        'id="person-card-portrait"' in body,
        'id="person-list"' in body,
        f'id="tree-card-{lena.pk}"' in body,
        "Passt. Das Foto ist da." in body,
    ) == (True, True, True, True, True, True, True)


@pytest.mark.django_db
def test_photo_create_view_counts_several_photos(admin_client):
    lena = PersonFactory()

    body = _post(
        admin_client, reverse("family_tree:photo-create-view", kwargs={"pk": lena.pk}), {"files": [_jpeg(), _jpeg()]}
    )

    assert "Passt. 2 Fotos sind da." in body


@pytest.mark.django_db
def test_photo_create_view_keeps_the_search_running_in_the_list(admin_client):
    lena = PersonFactory(given_names="Lena")

    body = _post(
        admin_client,
        reverse("family_tree:photo-create-view", kwargs={"pk": lena.pk}),
        {"files": [_jpeg()], "search": " Lena "},
    )

    assert '"filtered":true' in body


@pytest.mark.django_db
def test_photo_create_view_asks_for_a_file_first(admin_client):
    lena = PersonFactory()

    body = _post(admin_client, reverse("family_tree:photo-create-view", kwargs={"pk": lena.pk}), {})

    assert "Such zuerst ein Foto aus." in body


@pytest.mark.django_db
def test_photo_create_view_refuses_somebody_not_in_the_tree(admin_client):
    body = _post(admin_client, reverse("family_tree:photo-create-view", kwargs={"pk": 404}), {"files": [_jpeg()]})

    assert "Diese Person ist nicht mehr im Baum." in body


@pytest.mark.django_db
def test_photo_create_view_refuses_a_file_that_is_no_photo(admin_client):
    lena = PersonFactory()

    body = _post(
        admin_client,
        reverse("family_tree:photo-create-view", kwargs={"pk": lena.pk}),
        {"files": [SimpleUploadedFile("Taufschein.pdf", b"%PDF-1.4")]},
    )

    assert (Photo.objects.exists(), "Fotos bitte als JPEG, PNG oder WebP" in body) == (False, True)


@pytest.mark.django_db
def test_photo_portrait_view_makes_the_photo_the_portrait(admin_client):
    link = PhotoPersonFactory()

    body = _post(
        admin_client,
        reverse("family_tree:photo-portrait-view", kwargs={"pk": link.person.pk, "photo_pk": link.photo.pk}),
        {},
    )

    assert (PhotoPerson.objects.get(pk=link.pk).is_portrait, "Passt. Das ist jetzt das Titelbild." in body) == (
        True,
        True,
    )


@pytest.mark.django_db
def test_photo_portrait_view_of_a_photo_no_longer_there_says_so(admin_client):
    lena = PersonFactory()

    body = _post(admin_client, reverse("family_tree:photo-portrait-view", kwargs={"pk": lena.pk, "photo_pk": 404}), {})

    assert "Dieses Foto ist nicht mehr da." in body


@pytest.mark.django_db
def test_photo_describe_view_saves_and_patches_the_tab(admin_client):
    link = PhotoPersonFactory()

    body = _post(
        admin_client,
        reverse("family_tree:photo-describe-view", kwargs={"pk": link.person.pk, "photo_pk": link.photo.pk}),
        {"description": "Am Hof", "day": "", "month": "", "year": "1950", "about": "on"},
    )

    assert Photo.objects.filter(pk=link.photo.pk, description="Am Hof", date_kind="about").exists() is True
    assert ('id="person-card-photo-list"' in body, "Passt. Ist gespeichert." in body) == (True, True)


@pytest.mark.django_db
def test_photo_describe_view_refuses_a_date_that_is_none(admin_client):
    link = PhotoPersonFactory()

    body = _post(
        admin_client,
        reverse("family_tree:photo-describe-view", kwargs={"pk": link.person.pk, "photo_pk": link.photo.pk}),
        {"description": "Am Hof", "day": "30", "month": "2", "year": "1950"},
    )

    assert (Photo.objects.get(pk=link.photo.pk).description, "30.2.1950 ist kein gültiges Datum." in body) == ("", True)


@pytest.mark.django_db
def test_photo_describe_view_of_a_photo_no_longer_there_says_so(admin_client):
    lena = PersonFactory()

    body = _post(
        admin_client,
        reverse("family_tree:photo-describe-view", kwargs={"pk": lena.pk, "photo_pk": 404}),
        {"description": "Am Hof"},
    )

    assert "Dieses Foto ist nicht mehr da." in body


@pytest.mark.django_db
def test_photo_describe_view_patches_nothing_for_a_person_no_longer_there(admin_client):
    photo = PhotoFactory()

    body = _post(
        admin_client,
        reverse("family_tree:photo-describe-view", kwargs={"pk": 404, "photo_pk": photo.pk}),
        {"description": "Am Hof"},
    )

    assert ("person-card-photo-list" in body, "Passt. Ist gespeichert." in body) == (False, True)


@pytest.mark.django_db
def test_photo_describe_view_does_not_patch_a_tree_card_the_tree_does_not_show(admin_client):
    TreeSettingsFactory()
    stranger = PhotoPersonFactory()

    body = _post(
        admin_client,
        reverse("family_tree:photo-describe-view", kwargs={"pk": stranger.person.pk, "photo_pk": stranger.photo.pk}),
        {"description": "Am Hof"},
    )

    assert f"tree-card-{stranger.person.pk}" not in body
