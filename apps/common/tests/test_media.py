import io
import re
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import ExifTags, Image
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Text
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NullObject,
    NumberObject,
    TextStringObject,
)

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
    exif[ExifTags.Base.Artist] = "Josef Erfunden"
    exif[ExifTags.Base.Make] = "Kamerafirma"
    exif[ExifTags.Base.Model] = "Modell X"
    exif[ExifTags.Base.Orientation] = 6
    exif.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.DateTimeOriginal] = "1931:05:01 10:00:00"
    exif.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.BodySerialNumber] = "SN-0001"
    exif.get_ifd(ExifTags.IFD.GPSInfo)[ExifTags.GPS.GPSLatitude] = (47.0, 30.0, 0.0)
    output = io.BytesIO()
    Image.new("RGB", (16, 8), "green").save(output, image_format, exif=exif)

    return output.getvalue()


def _tiff_with_tags() -> bytes:
    """
    An invented scan, turned on its side, whose TIFF tags name the scanner and the person who scanned it.
    Written through "tiffinfo", which is where a TIFF keeps them - Pillow puts no EXIF sub-blocks into one.
    """
    output = io.BytesIO()
    Image.new("RGB", (16, 8), "white").save(
        output,
        "TIFF",
        tiffinfo={
            ExifTags.Base.Make: "Scannerfirma",
            ExifTags.Base.Artist: "Josef Erfunden",
            ExifTags.Base.Orientation: 6,
        },
    )

    return output.getvalue()


def _pdf(*, pages: int = 1) -> bytes:
    """
    An invented certificate carrying everything the upload has to strip - the document information, XMP on
    the document, on a page and on a picture it draws, an editor's "PieceInfo", a bookmark, an embedded
    file, a comment's author, a file attachment and a broken entry among the annotations - around pages
    whose content it has to keep.
    """
    writer = PdfWriter()
    for number in range(pages):
        page = writer.add_blank_page(width=200, height=100)
        content = DecodedStreamObject()
        content.set_data(f"BT /F1 12 Tf 10 50 Td (Seite {number + 1}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(content)
    writer.pages[0].rotate(90)
    picture = DecodedStreamObject()
    picture.set_data(b"\x00")
    picture.update(
        {
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Image"),
            NameObject("/Width"): NumberObject(1),
            NameObject("/Height"): NumberObject(1),
            NameObject("/ColorSpace"): NameObject("/DeviceGray"),
            NameObject("/BitsPerComponent"): NumberObject(8),
        }
    )
    writer.add_metadata(
        {
            "/Author": "Josef Erfunden",
            "/Title": "Taufschein Josef Erfunden",
            "/Creator": "Scanner-App",
            "/Producer": "Scannerfirma",
            "/CreationDate": "D:20240501100000",
        }
    )
    xmp = DecodedStreamObject()
    xmp.set_data(b"<x:xmpmeta><dc:creator>Josef Erfunden</dc:creator></x:xmpmeta>")
    xmp.update({NameObject("/Type"): NameObject("/Metadata"), NameObject("/Subtype"): NameObject("/XML")})
    piece_info = DictionaryObject(
        {
            NameObject("/Editor"): DictionaryObject(
                {
                    NameObject("/LastModified"): TextStringObject("D:20240501100000"),
                    NameObject("/Private"): TextStringObject("Erfunden"),
                }
            )
        }
    )
    writer.root_object[NameObject("/Metadata")] = writer._add_object(xmp)
    writer.pages[0][NameObject("/Metadata")] = writer._add_object(xmp)
    writer.pages[0][NameObject("/PieceInfo")] = piece_info
    picture[NameObject("/Metadata")] = writer._add_object(xmp)
    picture[NameObject("/PieceInfo")] = piece_info
    # The same picture under two names, as a page that shows a stamp twice has it.
    picture_reference = writer._add_object(picture)
    writer.pages[0][NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/XObject"): DictionaryObject(
                {NameObject("/Im0"): picture_reference, NameObject("/Im1"): picture_reference}
            )
        }
    )
    writer.add_outline_item("Josef Erfunden", 0)
    writer.add_attachment("Josef Erfunden.txt", b"Josef Erfunden")
    comment = Text(rect=(10, 10, 30, 30), text="Seite 1 ist die Vorderseite")
    comment[NameObject("/T")] = TextStringObject("Josef Erfunden")
    writer.add_annotation(page_number=0, annotation=comment)
    attachment = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/FileAttachment"),
            NameObject("/Rect"): ArrayObject(),
            NameObject("/Contents"): TextStringObject("Anhang"),
        }
    )
    writer.add_annotation(page_number=0, annotation=attachment)
    writer.pages[0]["/Annots"].append(NullObject())
    output = io.BytesIO()
    writer.write(output)

    return output.getvalue()


def _stored_pdf(*, media_root: Path, name: str) -> tuple[bytes, PdfReader]:
    content = (media_root / name).read_bytes()

    return content, PdfReader(io.BytesIO(content))


def _stored_exif(*, media_root: Path, name: str) -> Image.Exif:
    return Image.open(media_root / name).getexif()


def test_store_upload_stores_the_file_at_the_name_with_its_extension(media_root):
    upload = SimpleUploadedFile("Oma Huber Taufe.JPG", _image_with_exif(image_format="JPEG"))

    name = store_upload(uploaded_file=upload, name="photos/17/original")

    assert name == "photos/17/original.jpg"
    assert (media_root / name).is_file()


def test_store_upload_stores_one_extension_per_kind(media_root):
    upload = SimpleUploadedFile("scan.TIFF", _tiff_with_tags())

    name = store_upload(uploaded_file=upload, name="sources/8/3")

    assert name == "sources/8/3.tif"


def test_store_upload_replaces_a_file_of_another_kind_at_the_name(media_root):
    first = SimpleUploadedFile("foto.png", _image_with_exif(image_format="PNG"))
    second = SimpleUploadedFile("foto.jpg", _image_with_exif(image_format="JPEG"))
    store_upload(uploaded_file=first, name="photos/17/original")

    store_upload(uploaded_file=second, name="photos/17/original")

    assert sorted(path.name for path in (media_root / "photos" / "17").iterdir()) == ["original.jpg"]


def test_store_upload_replaces_a_file_already_at_the_name(media_root):
    first = SimpleUploadedFile("urkunde.pdf", _pdf(pages=1))
    second = SimpleUploadedFile("urkunde.pdf", _pdf(pages=2))
    store_upload(uploaded_file=first, name="sources/8/3")

    name = store_upload(uploaded_file=second, name="sources/8/3")

    assert name == "sources/8/3.pdf"
    assert len(_stored_pdf(media_root=media_root, name=name)[1].pages) == 2


def test_store_upload_removes_the_location_from_a_jpeg(media_root):
    upload = SimpleUploadedFile("foto.jpg", _image_with_exif(image_format="JPEG"))

    name = store_upload(uploaded_file=upload, name="photos/1/original")

    assert dict(_stored_exif(media_root=media_root, name=name).get_ifd(ExifTags.IFD.GPSInfo)) == {}


def test_store_upload_removes_the_camera_from_a_jpeg(media_root):
    upload = SimpleUploadedFile("foto.jpg", _image_with_exif(image_format="JPEG"))

    name = store_upload(uploaded_file=upload, name="photos/1/original")

    exif = _stored_exif(media_root=media_root, name=name)
    assert (exif.get(ExifTags.Base.Make), exif.get(ExifTags.Base.Model)) == (None, None)
    assert ExifTags.Base.BodySerialNumber not in exif.get_ifd(ExifTags.IFD.Exif)


def test_store_upload_keeps_the_date_and_orientation_of_a_jpeg(media_root):
    upload = SimpleUploadedFile("foto.jpg", _image_with_exif(image_format="JPEG"))

    name = store_upload(uploaded_file=upload, name="photos/1/original")

    exif = _stored_exif(media_root=media_root, name=name)
    assert exif.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.DateTimeOriginal] == "1931:05:01 10:00:00"
    assert exif[ExifTags.Base.Orientation] == 6


def test_store_upload_removes_the_location_from_a_png(media_root):
    upload = SimpleUploadedFile("scan.png", _image_with_exif(image_format="PNG"))

    name = store_upload(uploaded_file=upload, name="sources/1/1")

    assert dict(_stored_exif(media_root=media_root, name=name).get_ifd(ExifTags.IFD.GPSInfo)) == {}


def test_store_upload_keeps_no_name_from_a_jpeg(media_root):
    upload = SimpleUploadedFile("foto.jpg", _image_with_exif(image_format="JPEG"))

    name = store_upload(uploaded_file=upload, name="photos/1/original")

    assert ExifTags.Base.Artist not in _stored_exif(media_root=media_root, name=name)


def test_store_upload_drops_the_comment_of_a_jpeg(media_root):
    output = io.BytesIO()
    Image.new("RGB", (8, 8)).save(output, "JPEG", comment=b"Taufe Josef Erfunden, Hallstatt")
    upload = SimpleUploadedFile("foto.jpg", output.getvalue())

    name = store_upload(uploaded_file=upload, name="photos/1/original")

    assert Image.open(media_root / name).info.get("comment") is None


def test_store_upload_takes_a_camera_jpeg_with_previews(media_root):
    output = io.BytesIO()
    Image.new("RGB", (16, 8)).save(output, "MPO", save_all=True, append_images=[Image.new("RGB", (4, 2))])
    upload = SimpleUploadedFile("kamera.jpg", output.getvalue())

    name = store_upload(uploaded_file=upload, name="photos/1/original")

    assert Image.open(media_root / name).format == "JPEG"


def test_store_upload_removes_the_location_from_a_webp(media_root):
    upload = SimpleUploadedFile("foto.webp", _image_with_exif(image_format="WEBP"))

    name = store_upload(uploaded_file=upload, name="photos/1/original")

    assert dict(_stored_exif(media_root=media_root, name=name).get_ifd(ExifTags.IFD.GPSInfo)) == {}


def test_store_upload_turns_a_tiff_upright(media_root):
    upload = SimpleUploadedFile("scan.tif", _tiff_with_tags())

    name = store_upload(uploaded_file=upload, name="sources/1/1")

    assert Image.open(media_root / name).size == (8, 16)


def test_store_upload_drops_the_tags_of_a_tiff(media_root):
    upload = SimpleUploadedFile("scan.tif", _tiff_with_tags())

    name = store_upload(uploaded_file=upload, name="sources/1/1")

    tags = Image.open(media_root / name).getexif()
    assert (tags.get(ExifTags.Base.Make), tags.get(ExifTags.Base.Artist)) == (None, None)


def test_store_upload_refuses_a_scan_with_several_pages(media_root):
    output = io.BytesIO()
    Image.new("RGB", (8, 8)).save(output, "TIFF", save_all=True, append_images=[Image.new("RGB", (8, 8))])
    upload = SimpleUploadedFile("urkunde.tif", output.getvalue())

    with pytest.raises(UploadRefusedError, match="Mehrseitige Scans bitte als PDF"):
        store_upload(uploaded_file=upload, name="sources/1/1")


def test_store_upload_keeps_the_pages_of_a_pdf(media_root):
    upload = SimpleUploadedFile("Urkunde Josef Erfunden.pdf", _pdf(pages=2))

    name = store_upload(uploaded_file=upload, name="sources/1/1")

    first, second = _stored_pdf(media_root=media_root, name=name)[1].pages
    assert (first.get_contents().get_data(), first.rotation, first.mediabox) == (
        b"BT /F1 12 Tf 10 50 Td (Seite 1) Tj ET",
        90,
        [0, 0, 200, 100],
    )
    assert (second.get_contents().get_data(), second.rotation) == (b"BT /F1 12 Tf 10 50 Td (Seite 2) Tj ET", 0)


def test_store_upload_keeps_no_name_anywhere_in_a_pdf(media_root):
    upload = SimpleUploadedFile("urkunde.pdf", _pdf())

    name = store_upload(uploaded_file=upload, name="sources/1/1")

    assert b"Erfunden" not in _stored_pdf(media_root=media_root, name=name)[0]


def test_store_upload_drops_the_document_information_of_a_pdf(media_root):
    upload = SimpleUploadedFile("urkunde.pdf", _pdf())

    name = store_upload(uploaded_file=upload, name="sources/1/1")

    content, reader = _stored_pdf(media_root=media_root, name=name)
    assert (reader.metadata, b"Scanner" in content, b"pypdf" in content) == (None, False, False)


def test_store_upload_keeps_only_the_pages_of_a_pdf(media_root):
    upload = SimpleUploadedFile("urkunde.pdf", _pdf())

    name = store_upload(uploaded_file=upload, name="sources/1/1")

    reader = _stored_pdf(media_root=media_root, name=name)[1]
    assert (set(reader.trailer["/Root"]), set(reader.pages[0])) == (
        {"/Type", "/Pages"},
        {"/Type", "/Parent", "/Resources", "/MediaBox", "/Contents", "/Rotate", "/Annots"},
    )


def test_store_upload_keeps_a_comment_in_a_pdf_without_its_author(media_root):
    upload = SimpleUploadedFile("urkunde.pdf", _pdf())

    name = store_upload(uploaded_file=upload, name="sources/1/1")

    (comment,) = _stored_pdf(media_root=media_root, name=name)[1].pages[0]["/Annots"]
    comment = comment.get_object()
    assert (comment["/Subtype"], comment["/Contents"], "/T" in comment) == (
        "/Text",
        "Seite 1 ist die Vorderseite",
        False,
    )


def test_store_upload_keeps_what_a_pdf_page_draws_under_the_names_of_metadata(media_root):
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=100)
    font = DictionaryObject(
        {NameObject("/Type"): NameObject("/Font"), NameObject("/BaseFont"): NameObject("/Helvetica")}
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/Metadata"): writer._add_object(font), NameObject("/PieceInfo"): writer._add_object(font)}
            )
        }
    )
    output = io.BytesIO()
    writer.write(output)
    upload = SimpleUploadedFile("urkunde.pdf", output.getvalue())

    name = store_upload(uploaded_file=upload, name="sources/1/1")

    fonts = _stored_pdf(media_root=media_root, name=name)[1].pages[0]["/Resources"]["/Font"]
    assert set(fonts) == {"/Metadata", "/PieceInfo"}


def test_store_upload_refuses_a_pdf_that_does_not_open(media_root):
    upload = SimpleUploadedFile("urkunde.pdf", b"%PDF-1.4\nerfunden, aber kaputt")

    with pytest.raises(UploadRefusedError, match="PDF lässt sich nicht lesen"):
        store_upload(uploaded_file=upload, name="sources/1/1")


def test_store_upload_refuses_a_pdf_whose_pages_do_not_open(media_root):
    # The page tree points at a number where its list of pages belongs.
    broken = re.sub(rb"/Kids \[[^\]]*\]", b"/Kids 5", _pdf())
    upload = SimpleUploadedFile("urkunde.pdf", broken)

    with pytest.raises(UploadRefusedError, match="PDF lässt sich nicht lesen"):
        store_upload(uploaded_file=upload, name="sources/1/1")


def test_store_upload_refuses_an_encrypted_pdf(media_root):
    writer = PdfWriter(clone_from=io.BytesIO(_pdf()))
    writer.encrypt(user_password="erfunden")
    output = io.BytesIO()
    writer.write(output)
    upload = SimpleUploadedFile("urkunde.pdf", output.getvalue())

    with pytest.raises(UploadRefusedError, match="PDF ist verschlüsselt"):
        store_upload(uploaded_file=upload, name="sources/1/1")


def test_store_upload_refuses_a_pdf_that_is_none(media_root):
    upload = SimpleUploadedFile("urkunde.pdf", b"kein PDF")

    with pytest.raises(UploadRefusedError, match="ist aber kein PDF"):
        store_upload(uploaded_file=upload, name="sources/1/1")


def test_store_upload_refuses_an_unknown_kind_of_file(media_root):
    upload = SimpleUploadedFile("notiz.docx", b"PK")

    with pytest.raises(UploadRefusedError, match="JPEG, PNG, WebP, TIFF oder PDF"):
        store_upload(uploaded_file=upload, name="sources/1/1")


def test_store_upload_refuses_an_image_that_does_not_open(media_root):
    upload = SimpleUploadedFile("foto.jpg", b"kein Bild")

    with pytest.raises(UploadRefusedError, match="nicht als Bild öffnen"):
        store_upload(uploaded_file=upload, name="photos/1/original")


def test_store_upload_refuses_an_image_under_the_wrong_extension(media_root):
    upload = SimpleUploadedFile("foto.jpg", _image_with_exif(image_format="PNG"))

    with pytest.raises(UploadRefusedError, match="passt nicht zum Inhalt"):
        store_upload(uploaded_file=upload, name="photos/1/original")
