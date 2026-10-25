import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.family_tree.models import Person
from apps.family_tree.tests.factories.person import PersonFactory

DATASTAR = {"Datastar-Request": "true"}
GEDCOM = b"0 HEAD\n1 SOUR PAF\n0 @I1@ INDI\n1 NAME Lena /Huber/\n0 TRLR\n"


def _events(response) -> str:
    return b"".join(response.streaming_content).decode()


def _file(content: bytes = GEDCOM) -> SimpleUploadedFile:
    return SimpleUploadedFile("huber.ged", content, content_type="application/octet-stream")


@pytest.mark.django_db
def test_gedcom_import_dialog_view_appends_the_dialog(admin_client):
    response = admin_client.get(reverse("family_tree:gedcom-import-dialog-view"), headers=DATASTAR)

    body = _events(response)
    assert response.status_code == 200
    assert "selector body" in body and "mode append" in body and 'id="gedcom-import-dialog"' in body


@pytest.mark.django_db
def test_gedcom_preview_view_patches_what_the_file_brings(admin_client):
    response = admin_client.post(reverse("family_tree:gedcom-preview-view"), {"file": _file()}, headers=DATASTAR)

    body = _events(response)
    assert 'id="gedcom-import-preview"' in body and "Aus PAF erkannt" in body
    assert Person.objects.exists() is False


@pytest.mark.django_db
def test_gedcom_preview_view_asks_for_a_file(admin_client):
    response = admin_client.post(reverse("family_tree:gedcom-preview-view"), {}, headers=DATASTAR)

    assert "Such zuerst eine GEDCOM-Datei aus." in _events(response)


@pytest.mark.django_db
def test_gedcom_preview_view_refuses_a_file_that_is_not_gedcom(admin_client):
    response = admin_client.post(
        reverse("family_tree:gedcom-preview-view"), {"file": _file(b"0 HEAD\nLiebe Oma,\n0 TRLR\n")}, headers=DATASTAR
    )

    assert "keine GEDCOM-Datei" in _events(response)


@pytest.mark.django_db
def test_gedcom_import_view_imports_and_leads_to_the_tree(admin_client):
    response = admin_client.post(
        reverse("family_tree:gedcom-import-view"), {"file": _file(), "name": "PAF Huber"}, headers=DATASTAR
    )

    body = _events(response)
    assert reverse("family_tree:start-view") in body and Person.objects.get().given_names == "Lena"
    assert admin_client.session["_toasts"] == [{"text": "Passt. „PAF Huber“ ist importiert.", "style": "success"}]


@pytest.mark.django_db
def test_gedcom_import_view_asks_for_a_file(admin_client):
    response = admin_client.post(reverse("family_tree:gedcom-import-view"), {"name": "PAF Huber"}, headers=DATASTAR)

    assert "Such zuerst eine GEDCOM-Datei aus." in _events(response)


@pytest.mark.django_db
def test_gedcom_import_view_answers_a_refusal_with_its_reason(admin_client):
    PersonFactory()

    response = admin_client.post(
        reverse("family_tree:gedcom-import-view"), {"file": _file(), "name": "PAF Huber"}, headers=DATASTAR
    )

    assert "nur in einen leeren Stammbaum" in _events(response)
