from pathlib import Path

import pytest
from django.http import Http404
from django.urls import reverse
from pytest_django.asserts import assertRedirects

from apps.common.views.media import media_view


@pytest.fixture
def media_root(settings, tmp_path) -> Path:
    media_root = tmp_path / "medien"
    (media_root / "fotos").mkdir(parents=True)
    (media_root / "fotos" / "abc.jpg").write_bytes(b"erfundenes Foto")
    (tmp_path / "geheim.txt").write_text("nicht in den Medien")
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


def test_media_view_refuses_a_path_out_of_the_media_directory(rf, media_root):
    """
    Called directly: through the client, the URL would be normalised before it reached the view.
    """
    with pytest.raises(Http404):
        media_view(rf.get("/"), path="../geheim.txt")


def test_media_view_refuses_a_symlink_out_of_the_media_directory(rf, media_root):
    (media_root / "fotos" / "link.txt").symlink_to(media_root.parent / "geheim.txt")

    with pytest.raises(Http404):
        media_view(rf.get("/"), path="fotos/link.txt")


@pytest.mark.django_db
def test_media_view_leaves_the_bytes_to_nginx_behind_a_proxy(admin_client, media_root, settings):
    settings.ZWEIGERL_MEDIA_ACCEL_PREFIX = "/_medien/"

    response = admin_client.get(reverse("common:media-view", kwargs={"path": "fotos/abc.jpg"}))

    assert response["X-Accel-Redirect"] == "/_medien/fotos/abc.jpg"
    assert response.content == b""
