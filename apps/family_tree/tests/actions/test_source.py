import io
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.common.media import UploadRefusedError
from apps.family_tree.actions.source import add_source_files, create_source
from apps.family_tree.models import Person, Source, SourceFile
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.source import SourceFactory

PDF = b"%PDF-1.4 erfundene Geburtsurkunde"


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path) -> Path:
    settings.MEDIA_ROOT = tmp_path

    return tmp_path


def _png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (4, 4), "white").save(output, "PNG")

    return output.getvalue()


@pytest.mark.django_db
def test_create_source_files_the_source_with_the_person():
    lena = PersonFactory()

    source = create_source(
        person_id=lena.pk, title=" Geburtsurkunde Lena ", kind="civil_registry", description=" Nr. 1989/3471 ", files=[]
    )

    assert (source.title, source.kind, source.description, list(source.people.all())) == (
        "Geburtsurkunde Lena",
        "civil_registry",
        "Nr. 1989/3471",
        [lena],
    )


@pytest.mark.django_db
def test_create_source_stores_each_file_under_the_ids(media_root):
    lena = PersonFactory()

    source = create_source(
        person_id=lena.pk,
        title="Taufbuch",
        kind="parish_register",
        description="",
        files=[SimpleUploadedFile("Taufe Lena Huber.pdf", PDF), SimpleUploadedFile("Seite 2.png", _png())],
    )

    first, second = source.files.all()
    assert [first.file.name, second.file.name] == [
        f"sources/{source.pk}/{first.pk}.pdf",
        f"sources/{source.pk}/{second.pk}.png",
    ]
    assert (media_root / first.file.name).read_bytes() == PDF


@pytest.mark.django_db
def test_create_source_refuses_somebody_not_in_the_tree():
    with pytest.raises(Person.DoesNotExist, match="Person matching query does not exist"):
        create_source(person_id=404, title="Taufbuch", kind="other", description="", files=[])


@pytest.mark.django_db
def test_create_source_refuses_a_missing_title():
    lena = PersonFactory()

    with pytest.raises(ValidationError, match="Eine Quelle braucht einen Titel"):
        create_source(person_id=lena.pk, title="   ", kind="other", description="", files=[])


@pytest.mark.django_db
def test_create_source_refusing_a_file_leaves_nothing_behind(media_root):
    lena = PersonFactory()

    with pytest.raises(UploadRefusedError, match="JPEG, PNG, WebP, TIFF oder PDF"):
        create_source(
            person_id=lena.pk,
            title="Taufbuch",
            kind="other",
            description="",
            files=[SimpleUploadedFile("Urkunde.pdf", PDF), SimpleUploadedFile("Notiz.txt", b"erfunden")],
        )

    assert (Source.objects.exists(), list(media_root.rglob("*.pdf"))) == (False, [])


@pytest.mark.django_db
def test_add_source_files_attaches_the_files(media_root):
    source = SourceFactory()

    stored = add_source_files(source_id=source.pk, files=[SimpleUploadedFile("Scan.pdf", PDF)])

    assert list(source.files.all()) == stored
    assert (media_root / stored[0].file.name).read_bytes() == PDF


@pytest.mark.django_db
def test_add_source_files_refuses_a_source_that_is_gone():
    with pytest.raises(Source.DoesNotExist, match="Source matching query does not exist"):
        add_source_files(source_id=404, files=[SimpleUploadedFile("Scan.pdf", PDF)])


@pytest.mark.django_db
def test_add_source_files_refusing_a_file_attaches_none():
    source = SourceFactory()

    with pytest.raises(UploadRefusedError, match="ist aber kein PDF"):
        add_source_files(source_id=source.pk, files=[SimpleUploadedFile("Scan.pdf", b"kein pdf")])

    assert SourceFile.objects.exists() is False
