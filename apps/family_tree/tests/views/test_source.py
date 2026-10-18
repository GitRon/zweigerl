from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.family_tree.models import Source, SourceFile
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.source import SourceFactory

PDF = b"%PDF-1.4 erfundene Geburtsurkunde"


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path) -> Path:
    settings.MEDIA_ROOT = tmp_path

    return tmp_path


def _post(client, url: str, data: dict) -> str:
    response = client.post(url, data, headers={"Datastar-Request": "true"})

    return b"".join(response.streaming_content).decode()


@pytest.mark.django_db
def test_source_create_view_creates_the_source_and_patches_the_card(admin_client):
    lena = PersonFactory()

    body = _post(
        admin_client,
        reverse("family_tree:source-create-view", kwargs={"pk": lena.pk}),
        {
            "title": "Geburtsurkunde",
            "kind": "civil_registry",
            "description": "",
            "files": [SimpleUploadedFile("a.pdf", PDF)],
        },
    )

    assert list(Source.objects.values_list("title", flat=True)) == ["Geburtsurkunde"]
    assert 'id="person-card"' in body and "Passt. „Geburtsurkunde“ liegt jetzt bei den Quellen." in body


@pytest.mark.django_db
def test_source_create_view_refuses_somebody_not_in_the_tree(admin_client):
    body = _post(admin_client, reverse("family_tree:source-create-view", kwargs={"pk": 404}), {"title": "Taufbuch"})

    assert "Diese Person ist nicht mehr im Baum." in body


@pytest.mark.django_db
def test_source_create_view_refuses_a_source_without_a_title(admin_client):
    lena = PersonFactory()

    body = _post(
        admin_client, reverse("family_tree:source-create-view", kwargs={"pk": lena.pk}), {"title": "", "kind": "other"}
    )

    assert "Eine Quelle braucht einen Titel." in body


@pytest.mark.django_db
def test_source_create_view_refuses_a_file_zweigerl_does_not_keep(admin_client):
    lena = PersonFactory()

    body = _post(
        admin_client,
        reverse("family_tree:source-create-view", kwargs={"pk": lena.pk}),
        {"title": "Taufbuch", "kind": "other", "files": [SimpleUploadedFile("Notiz.txt", b"erfunden")]},
    )

    assert (Source.objects.exists(), "Zweigerl nimmt Fotos und Scans" in body) == (False, True)


@pytest.mark.django_db
def test_source_files_view_attaches_the_files_and_patches_the_card(admin_client):
    lena = PersonFactory()
    source = SourceFactory(people=[lena])

    body = _post(
        admin_client,
        reverse("family_tree:source-files-view", kwargs={"pk": lena.pk, "source_pk": source.pk}),
        {"files": [SimpleUploadedFile("Scan.pdf", PDF)]},
    )

    assert source.files.count() == 1
    assert 'id="person-card"' in body and "Passt. Hängt jetzt an der Quelle." in body


@pytest.mark.django_db
def test_source_files_view_asks_for_a_file_first(admin_client):
    lena = PersonFactory()
    source = SourceFactory(people=[lena])

    body = _post(
        admin_client, reverse("family_tree:source-files-view", kwargs={"pk": lena.pk, "source_pk": source.pk}), {}
    )

    assert "Such zuerst eine Datei aus." in body


@pytest.mark.django_db
def test_source_files_view_refuses_a_source_that_is_gone(admin_client):
    lena = PersonFactory()

    body = _post(
        admin_client,
        reverse("family_tree:source-files-view", kwargs={"pk": lena.pk, "source_pk": 404}),
        {"files": [SimpleUploadedFile("Scan.pdf", PDF)]},
    )

    assert "Diese Quelle ist nicht mehr da." in body


@pytest.mark.django_db
def test_source_files_view_refuses_a_file_zweigerl_does_not_keep(admin_client):
    lena = PersonFactory()
    source = SourceFactory(people=[lena])

    body = _post(
        admin_client,
        reverse("family_tree:source-files-view", kwargs={"pk": lena.pk, "source_pk": source.pk}),
        {"files": [SimpleUploadedFile("Scan.pdf", b"kein pdf")]},
    )

    assert (SourceFile.objects.exists(), "ist aber kein PDF" in body) == (False, True)


@pytest.mark.django_db
def test_source_files_view_patches_no_card_for_somebody_not_in_the_tree(admin_client):
    source = SourceFactory()

    body = _post(
        admin_client,
        reverse("family_tree:source-files-view", kwargs={"pk": 404, "source_pk": source.pk}),
        {"files": [SimpleUploadedFile("Scan.pdf", PDF)]},
    )

    assert ('id="person-card"' in body, "Passt. Hängt jetzt an der Quelle." in body) == (False, True)
