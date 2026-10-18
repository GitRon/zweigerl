from pathlib import Path

import pytest
from django.urls import reverse
from pytest_django.asserts import assertRedirects


@pytest.fixture
def media_root(settings, tmp_path) -> Path:
    media_root = tmp_path / "medien"
    (media_root / "fotos").mkdir(parents=True)
    (media_root / "fotos" / "abc.jpg").write_bytes(b"erfundenes Foto")
    (tmp_path / "geheim.jpg").write_bytes(b"nicht in den Medien")
    settings.MEDIA_ROOT = media_root

    return media_root


@pytest.mark.django_db
def test_media_view_hands_out_the_file_after_login(admin_client, media_root):
    response = admin_client.get(reverse("common:media-view", kwargs={"path": "fotos/abc.jpg"}))

    assert response.status_code == 200
    assert b"".join(response.streaming_content) == b"erfundenes Foto"
    assert response["Cache-Control"] == "private"


@pytest.mark.django_db
def test_media_view_sends_an_anonymous_visit_to_the_login(client, media_root):
    url = reverse("common:media-view", kwargs={"path": "fotos/abc.jpg"})

    response = client.get(url)

    assertRedirects(response, f"{reverse('common:login-view')}?next={url}")


@pytest.mark.django_db
def test_media_view_answers_404_for_a_missing_file(admin_client, media_root):
    response = admin_client.get(reverse("common:media-view", kwargs={"path": "fotos/gibtsnicht.jpg"}))

    assert response.status_code == 404


@pytest.mark.django_db
def test_media_view_answers_404_for_a_folder(admin_client, media_root):
    response = admin_client.get(reverse("common:media-view", kwargs={"path": "fotos"}))

    assert response.status_code == 404


@pytest.mark.django_db
def test_media_view_answers_404_for_a_path_out_of_the_media_directory(admin_client, media_root):
    response = admin_client.get("/medien/..%2fgeheim.jpg")

    assert response.status_code == 404


@pytest.mark.django_db
def test_media_view_answers_404_for_a_symlink_out_of_the_media_directory(admin_client, media_root):
    (media_root / "fotos" / "link.jpg").symlink_to(media_root.parent / "geheim.jpg")

    response = admin_client.get(reverse("common:media-view", kwargs={"path": "fotos/link.jpg"}))

    assert response.status_code == 404


@pytest.mark.django_db
def test_media_view_answers_404_for_a_kind_of_file_uploads_never_make(admin_client, media_root):
    (media_root / "fotos" / "seite.html").write_text("<script>alert(1)</script>")

    response = admin_client.get(reverse("common:media-view", kwargs={"path": "fotos/seite.html"}))

    assert response.status_code == 404


@pytest.mark.django_db
def test_media_view_answers_404_for_a_path_the_file_system_refuses(admin_client, media_root):
    response = admin_client.get("/medien/fotos/a%00b.jpg")

    assert response.status_code == 404


@pytest.mark.django_db
def test_media_view_leaves_the_bytes_to_nginx_behind_a_proxy(admin_client, media_root, settings):
    settings.ZWEIGERL_MEDIA_ACCEL_PREFIX = "/_medien/"

    response = admin_client.get(reverse("common:media-view", kwargs={"path": "fotos/abc.jpg"}))

    assert response["X-Accel-Redirect"] == "/_medien/fotos/abc.jpg"
    assert response.content == b""


@pytest.mark.django_db
def test_media_view_encodes_the_path_it_hands_to_nginx(admin_client, media_root, settings):
    (media_root / "fotos" / "a b?c#.jpg").write_bytes(b"erfundenes Foto")
    settings.ZWEIGERL_MEDIA_ACCEL_PREFIX = "/_medien"

    response = admin_client.get(reverse("common:media-view", kwargs={"path": "fotos/a b?c#.jpg"}))

    assert response["X-Accel-Redirect"] == "/_medien/fotos/a%20b%3Fc%23.jpg"
