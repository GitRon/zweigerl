import io
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from pypdf import PdfWriter

from apps.family_tree.models import Source, SourceFile
from apps.family_tree.tests.factories.citation import CitationFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.source import SourceFactory
from apps.family_tree.tests.factories.source_file import SourceFileFactory


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path) -> Path:
    settings.MEDIA_ROOT = tmp_path

    return tmp_path


def _pdf() -> bytes:
    """
    An invented certificate of one empty page; what "store_upload" strips from a PDF is tested in
    apps/common.
    """
    output = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=100)
    writer.write(output)

    return output.getvalue()


def _post(client, url: str, data: dict) -> str:
    response = client.post(url, data, headers={"Datastar-Request": "true"})

    return b"".join(response.streaming_content).decode()


@pytest.mark.django_db
def test_source_create_view_creates_the_source_and_patches_the_list(admin_client):
    lena = PersonFactory()

    body = _post(
        admin_client,
        reverse("family_tree:source-create-view", kwargs={"pk": lena.pk}),
        {
            "title": "Geburtsurkunde",
            "kind": "civil_registry",
            "description": "",
            "files": [SimpleUploadedFile("a.pdf", _pdf())],
        },
    )

    assert list(Source.objects.values_list("title", flat=True)) == ["Geburtsurkunde"]
    assert (
        "data: mode replace" in body,
        'id="person-card-source-list"' in body,
        "Passt. „Geburtsurkunde“ liegt jetzt bei den Quellen." in body,
    ) == (True, True, True)


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
def test_source_files_view_attaches_the_files_and_patches_the_list(admin_client):
    lena = PersonFactory()
    source = SourceFactory(people=[lena])

    body = _post(
        admin_client,
        reverse("family_tree:source-files-view", kwargs={"pk": lena.pk, "source_pk": source.pk}),
        {"files": [SimpleUploadedFile("Scan.pdf", _pdf())]},
    )

    assert source.files.count() == 1
    assert 'id="person-card-source-list"' in body and "Passt. Hängt jetzt an der Quelle." in body


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
        {"files": [SimpleUploadedFile("Scan.pdf", _pdf())]},
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
def test_source_files_view_patches_no_list_for_somebody_not_in_the_tree(admin_client):
    source = SourceFactory()

    body = _post(
        admin_client,
        reverse("family_tree:source-files-view", kwargs={"pk": 404, "source_pk": source.pk}),
        {"files": [SimpleUploadedFile("Scan.pdf", _pdf())]},
    )

    assert ('id="person-card-source-list"' in body, "Passt. Hängt jetzt an der Quelle." in body) == (False, True)


def _get(client, url: str):
    return client.get(url, headers={"Datastar-Request": "true"})


@pytest.mark.django_db
def test_delete_source_view_asks_first_in_a_dialog(admin_client):
    source = SourceFactory()

    body = b"".join(
        _get(
            admin_client,
            reverse("family_tree:delete-source-view", kwargs={"pk": PersonFactory().pk, "source_pk": source.pk}),
        ).streaming_content
    ).decode()

    assert ("selector body" in body, "mode append" in body, 'id="delete-source-dialog"' in body) == (True, True, True)


@pytest.mark.django_db
def test_delete_source_view_asks_about_a_source_not_there_not_at_all(admin_client):
    response = _get(
        admin_client, reverse("family_tree:delete-source-view", kwargs={"pk": PersonFactory().pk, "source_pk": 404})
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_delete_source_view_deletes_it_closes_the_dialog_and_patches_the_list(admin_client):
    lena = PersonFactory()
    source = SourceFactory(title="Taufbuch", people=[lena])

    body = _post(
        admin_client, reverse("family_tree:delete-source-view", kwargs={"pk": lena.pk, "source_pk": source.pk}), {}
    )

    assert Source.objects.exists() is False
    assert (
        "selector #delete-source-dialog" in body,
        'id="person-card-source-list"' in body,
        "Passt. „Taufbuch“ ist gelöscht." in body,
    ) == (True, True, True)


@pytest.mark.django_db
def test_delete_source_view_of_a_source_no_longer_there_says_so(admin_client):
    body = _post(
        admin_client, reverse("family_tree:delete-source-view", kwargs={"pk": PersonFactory().pk, "source_pk": 404}), {}
    )

    assert "Diese Quelle ist nicht mehr da." in body


@pytest.mark.django_db
def test_delete_source_view_of_a_cited_source_says_why_it_stays(admin_client):
    citation = CitationFactory(source__title="Taufbuch")

    body = _post(
        admin_client,
        reverse(
            "family_tree:delete-source-view", kwargs={"pk": citation.fact.person.pk, "source_pk": citation.source.pk}
        ),
        {},
    )

    assert "„Taufbuch“ wird noch zitiert und bleibt deshalb." in body


@pytest.mark.django_db
def test_delete_source_file_view_asks_first_in_a_dialog(admin_client):
    scan = SourceFileFactory()

    body = b"".join(
        _get(
            admin_client,
            reverse(
                "family_tree:delete-source-file-view",
                kwargs={"pk": PersonFactory().pk, "source_pk": scan.source.pk, "file_pk": scan.pk},
            ),
        ).streaming_content
    ).decode()

    assert ("mode append" in body, 'id="delete-source-file-dialog"' in body) == (True, True)


@pytest.mark.django_db
def test_delete_source_file_view_asks_about_a_file_not_there_not_at_all(admin_client):
    response = _get(
        admin_client,
        reverse(
            "family_tree:delete-source-file-view",
            kwargs={"pk": PersonFactory().pk, "source_pk": SourceFactory().pk, "file_pk": 404},
        ),
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_delete_source_file_view_removes_it_closes_the_dialog_and_patches_the_list(admin_client):
    lena = PersonFactory()
    scan = SourceFileFactory(source__people=[lena])

    body = _post(
        admin_client,
        reverse(
            "family_tree:delete-source-file-view",
            kwargs={"pk": lena.pk, "source_pk": scan.source.pk, "file_pk": scan.pk},
        ),
        {},
    )

    assert SourceFile.objects.exists() is False
    assert (
        "selector #delete-source-file-dialog" in body,
        'id="person-card-source-list"' in body,
        "Passt. Die Datei ist entfernt." in body,
    ) == (True, True, True)


@pytest.mark.django_db
def test_delete_source_file_view_of_a_file_no_longer_there_says_so(admin_client):
    body = _post(
        admin_client,
        reverse(
            "family_tree:delete-source-file-view",
            kwargs={"pk": PersonFactory().pk, "source_pk": SourceFactory().pk, "file_pk": 404},
        ),
        {},
    )

    assert "Diese Datei ist nicht mehr da." in body
