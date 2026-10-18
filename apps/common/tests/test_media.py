import io
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import ExifTags, Image

from apps.common.media import UploadRefusedError, store_upload


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path) -> Path:
    settings.MEDIA_ROOT = tmp_path

    return tmp_path


def _image_with_exif(*, image_format: str) -> bytes:
    """
    An invented photo carrying everything the upload has to strip, and the date it has to keep.
    """
    exif = Image.Exif()
    exif[ExifTags.Base.Make] = "Kamerafirma"
    exif[ExifTags.Base.Model] = "Modell X"
    exif[ExifTags.Base.Orientation] = 6
    exif.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.DateTimeOriginal] = "1931:05:01 10:00:00"
    exif.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.BodySerialNumber] = "SN-0001"
    exif.get_ifd(ExifTags.IFD.GPSInfo)[ExifTags.GPS.GPSLatitude] = (47.0, 30.0, 0.0)
    output = io.BytesIO()
    Image.new("RGB", (16, 8), "green").save(output, image_format, exif=exif)

    return output.getvalue()


def _stored_exif(*, media_root: Path, name: str) -> Image.Exif:
    return Image.open(media_root / name).getexif()


def test_store_upload_names_the_file_at_random_inside_the_folder(media_root):
    upload = SimpleUploadedFile("Oma Huber Taufe.JPG", _image_with_exif(image_format="JPEG"))

    name = store_upload(uploaded_file=upload, folder="fotos")

    assert Path(name).parent == Path("fotos")
    assert "Huber" not in name
    assert Path(name).suffix == ".jpg"


def test_store_upload_removes_the_location_from_a_jpeg(media_root):
    upload = SimpleUploadedFile("foto.jpg", _image_with_exif(image_format="JPEG"))

    name = store_upload(uploaded_file=upload, folder="fotos")

    assert dict(_stored_exif(media_root=media_root, name=name).get_ifd(ExifTags.IFD.GPSInfo)) == {}


def test_store_upload_removes_the_camera_from_a_jpeg(media_root):
    upload = SimpleUploadedFile("foto.jpg", _image_with_exif(image_format="JPEG"))

    name = store_upload(uploaded_file=upload, folder="fotos")

    exif = _stored_exif(media_root=media_root, name=name)
    assert (exif.get(ExifTags.Base.Make), exif.get(ExifTags.Base.Model)) == (None, None)
    assert ExifTags.Base.BodySerialNumber not in exif.get_ifd(ExifTags.IFD.Exif)


def test_store_upload_keeps_the_date_and_orientation_of_a_jpeg(media_root):
    upload = SimpleUploadedFile("foto.jpg", _image_with_exif(image_format="JPEG"))

    name = store_upload(uploaded_file=upload, folder="fotos")

    exif = _stored_exif(media_root=media_root, name=name)
    assert exif.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.DateTimeOriginal] == "1931:05:01 10:00:00"
    assert exif[ExifTags.Base.Orientation] == 6


def test_store_upload_removes_the_location_from_a_png(media_root):
    upload = SimpleUploadedFile("scan.png", _image_with_exif(image_format="PNG"))

    name = store_upload(uploaded_file=upload, folder="quellen")

    assert dict(_stored_exif(media_root=media_root, name=name).get_ifd(ExifTags.IFD.GPSInfo)) == {}


def test_store_upload_turns_a_tiff_upright_and_drops_its_tags(media_root):
    upload = SimpleUploadedFile("scan.tif", _image_with_exif(image_format="TIFF"))

    name = store_upload(uploaded_file=upload, folder="quellen")

    stored = Image.open(media_root / name)
    assert stored.size == (8, 16)
    assert dict(stored.getexif().get_ifd(ExifTags.IFD.GPSInfo)) == {}


def test_store_upload_keeps_a_pdf_as_it_came(media_root):
    pdf = b"%PDF-1.4\n% erfundene Urkunde\n%%EOF\n"
    upload = SimpleUploadedFile("Urkunde Josef Huber.pdf", pdf)

    name = store_upload(uploaded_file=upload, folder="quellen")

    assert (media_root / name).read_bytes() == pdf


def test_store_upload_refuses_a_pdf_that_is_none(media_root):
    upload = SimpleUploadedFile("urkunde.pdf", b"kein PDF")

    with pytest.raises(UploadRefusedError, match="ist aber kein PDF"):
        store_upload(uploaded_file=upload, folder="quellen")


def test_store_upload_refuses_an_unknown_kind_of_file(media_root):
    upload = SimpleUploadedFile("notiz.docx", b"PK")

    with pytest.raises(UploadRefusedError, match="JPEG, PNG, WebP, TIFF oder PDF"):
        store_upload(uploaded_file=upload, folder="quellen")


def test_store_upload_refuses_an_image_that_does_not_open(media_root):
    upload = SimpleUploadedFile("foto.jpg", b"kein Bild")

    with pytest.raises(UploadRefusedError, match="nicht als Bild öffnen"):
        store_upload(uploaded_file=upload, folder="fotos")


def test_store_upload_refuses_an_image_under_the_wrong_extension(media_root):
    upload = SimpleUploadedFile("foto.jpg", _image_with_exif(image_format="PNG"))

    with pytest.raises(UploadRefusedError, match="passt nicht zum Inhalt"):
        store_upload(uploaded_file=upload, folder="fotos")
