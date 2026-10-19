"""
Storing a photo or a scan: the one way an upload reaches the media directory.

See docs/patterns/data-storage.md, "Photos and scans".
"""

import io
from collections.abc import Iterable
from pathlib import PurePosixPath

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from PIL import ExifTags, Image, ImageOps, UnidentifiedImageError
from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.errors import PyPdfError
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, NameObject, StreamObject

# The extension a file is stored under, and the Pillow formats its content may have. A JPEG from many
# cameras and phones carries preview pictures (CIPA multi-picture) and opens as "MPO"; it is a JPEG all the
# same. PDFs are not images and are checked by their signature instead.
IMAGE_FORMATS = {
    "jpg": ("JPEG", "MPO"),
    "jpeg": ("JPEG", "MPO"),
    "png": ("PNG",),
    "webp": ("WEBP",),
    "tif": ("TIFF",),
    "tiff": ("TIFF",),
}
PDF_EXTENSION = "pdf"
# The one extension each kind is stored under, whatever the upload was called, so a file is found from its
# id and role alone and storing it again replaces it rather than leaving "3.tiff" beside "3.tif".
STORED_EXTENSIONS = {"jpg": "jpg", "jpeg": "jpg", "png": "png", "webp": "webp", "tif": "tif", "tiff": "tif"} | {
    PDF_EXTENSION: PDF_EXTENSION
}
PDF_SIGNATURE = b"%PDF-"
# What a page of a PDF keeps: what it draws and how big it is. Its XMP, the "PieceInfo" an editor leaves
# behind, thumbnails and links into a structure that is not copied all stay behind.
PDF_PAGE_KEYS = {
    "/Type",
    "/Resources",
    "/MediaBox",
    "/CropBox",
    "/BleedBox",
    "/TrimBox",
    "/ArtBox",
    "/Contents",
    "/Rotate",
    "/UserUnit",
    "/Annots",
}
# The annotations a page keeps: the ones that only mark something up or show a form as filled in. A file
# attachment, a sound, a movie or a link - which can run an action - does not come along.
PDF_ANNOTATION_SUBTYPES = {
    "/Text",
    "/FreeText",
    "/Line",
    "/Square",
    "/Circle",
    "/Polygon",
    "/PolyLine",
    "/Highlight",
    "/Underline",
    "/Squiggly",
    "/StrikeOut",
    "/Stamp",
    "/Caret",
    "/Ink",
    "/Widget",
}
# What such an annotation keeps: where it sits, what it looks like and the text it shows - not who wrote
# it, when, or the action and form field behind it.
PDF_ANNOTATION_KEYS = {
    "/Type",
    "/Subtype",
    "/Rect",
    "/Contents",
    "/AP",
    "/AS",
    "/F",
    "/Border",
    "/BS",
    "/BE",
    "/C",
    "/IC",
    "/CA",
    "/DA",
    "/Q",
    "/Name",
    "/QuadPoints",
    "/InkList",
    "/Vertices",
    "/L",
    "/LE",
    "/RD",
}
# A damaged PDF breaks pypdf in more ways than its own errors - a missing key, an object of the wrong type.
# Whichever it is, the file is refused rather than kept as it came. "UploadRefusedError" is a ValueError too,
# which is why nothing inside the "try" raises it.
_BROKEN_PDF = (PyPdfError, ValueError, KeyError, TypeError, AttributeError, IndexError, RecursionError)


class UploadRefusedError(ValueError):
    """
    The file is not one Zweigerl keeps. The message is meant for the person who uploaded it.
    """


def store_upload(*, uploaded_file: UploadedFile, name: str) -> str:
    """
    Stores a photo or a scan at "MEDIA_ROOT/<name>.<extension>" and returns the stored name, as a FileField
    wants it. "name" is the place in the layout without the extension - "photos/17/original" - and the caller
    builds it from ids, never from a person's name; see docs/patterns/data-storage.md, "Photos and scans".
    A file already there is replaced. The original file name is dropped: it often says who is in the
    picture. Images keep only the date they were taken and their orientation, PDFs only their pages.
    """
    extension = PurePosixPath(uploaded_file.name or "").suffix.lstrip(".").lower()
    content = uploaded_file.read()

    if extension in IMAGE_FORMATS:
        content = _picture_only(content=content, allowed_formats=IMAGE_FORMATS[extension])
    elif extension == PDF_EXTENSION:
        if not content.startswith(PDF_SIGNATURE):
            raise UploadRefusedError("Die Datei endet auf .pdf, ist aber kein PDF.")
        content = _pages_only(content=content)
    else:
        raise UploadRefusedError("Zweigerl nimmt Fotos und Scans als JPEG, PNG, WebP, TIFF oder PDF.")

    stored_name = default_storage.save(f"{name}.{STORED_EXTENSIONS[extension]}", ContentFile(content))
    # The storage overwrites a file of the same kind (STORAGES in the settings). One of another kind - a PNG
    # replaced by a JPEG - goes only after the new file is safely written.
    for other_extension in set(STORED_EXTENSIONS.values()) - {STORED_EXTENSIONS[extension]}:
        default_storage.delete(f"{name}.{other_extension}")

    return stored_name


def delete_on_commit(*, names: Iterable[str]) -> None:
    """
    Deletes the stored files "names" once the transaction around the caller commits - the way a file goes
    with its row (#72). Called after the rows are deleted, inside the same transaction: a rollback keeps the
    rows and with them their files, and a commit never leaves a file nobody sees. Outside a transaction the
    files go at once. A file already gone is no error.
    """
    names = list(names)

    def delete() -> None:
        for name in names:
            default_storage.delete(name)

    transaction.on_commit(delete)


def _picture_only(*, content: bytes, allowed_formats: tuple[str, ...]) -> bytes:
    """
    The image saved again with nothing but the picture, its colour profile, the date it was taken and its
    orientation. Whatever else a file carries - GPS, camera, serial numbers, the photographer's name, a
    description, comments, XMP - may name a person or a place, so it is not chosen what to drop but what to
    keep. See docs/patterns/data-storage.md, "Photos and scans".
    """
    try:
        image = Image.open(io.BytesIO(content))
        image.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as error:
        raise UploadRefusedError("Die Datei lässt sich nicht als Bild öffnen.") from error
    if image.format not in allowed_formats:
        raise UploadRefusedError("Die Dateiendung passt nicht zum Inhalt des Bildes.")
    # Saving keeps the first frame only. For the previews of an MPO that is the point; for a scan with
    # several pages or an animation it would lose pages without a word.
    if image.format != "MPO" and getattr(image, "n_frames", 1) > 1:
        raise UploadRefusedError("Mehrseitige Scans bitte als PDF hochladen.")

    image_format = "JPEG" if image.format == "MPO" else image.format
    options = {"icc_profile": image.info.get("icc_profile")}

    if image_format == "TIFF":
        # Pillow writes no EXIF sub-blocks into a TIFF, so the date taken cannot be kept there and the
        # orientation would be lost: it is applied to the pixels instead. A scan rarely has a date anyway.
        image = ImageOps.exif_transpose(image)
    else:
        options["exif"] = _date_and_orientation(exif=image.getexif())
    if image.format == "JPEG":
        # The quantisation tables of the original, so the picture is not visibly recompressed. An MPO has
        # none Pillow can reuse and is saved at a high quality instead.
        options["quality"] = "keep"
    elif image.format == "MPO":
        options["quality"] = 95
    if image_format == "JPEG":
        # Pillow carries a JPEG comment over unless told otherwise, and a comment is where names go.
        options["comment"] = b""

    output = io.BytesIO()
    image.save(output, image_format, **options)
    return output.getvalue()


def _pages_only(*, content: bytes) -> bytes:
    """
    The PDF written again from its pages and nothing else. The document information - author, title,
    creator, producer, the dates - its XMP, bookmarks, form fields, embedded files and scripts may name a
    person, a device or a program, so it is not chosen what to drop but what to keep: what each page shows.
    See docs/patterns/data-storage.md, "Photos and scans".
    """
    try:
        reader = PdfReader(io.BytesIO(content))
        encrypted = reader.is_encrypted
    except _BROKEN_PDF as error:
        raise UploadRefusedError("Das PDF lässt sich nicht lesen.") from error
    if encrypted:
        raise UploadRefusedError("Das PDF ist verschlüsselt. Bitte ohne Kennwort speichern und erneut hochladen.")

    try:
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(_page_only(page=page))
        # The writer starts with a document information of its own, naming itself as the producer.
        writer.metadata = None
        writer.pdf_header = reader.pdf_header
        output = io.BytesIO()
        writer.write(output)
    except _BROKEN_PDF as error:
        raise UploadRefusedError("Das PDF lässt sich nicht lesen.") from error

    return output.getvalue()


def _page_only(*, page: PageObject) -> PageObject:
    """
    The page of the reader cut down, in place, to what PDF_PAGE_KEYS and the two annotation sets keep and
    without XMP or an editor's private data below it, before the writer copies it - so what was cut is never
    copied in the first place.
    """
    for key in set(page) - PDF_PAGE_KEYS:
        del page[key]
    if "/Annots" in page:
        annotations = [annotation.get_object() for annotation in page["/Annots"].get_object()]
        page[NameObject("/Annots")] = ArrayObject(
            DictionaryObject(
                {NameObject(key): value for key, value in annotation.items() if key in PDF_ANNOTATION_KEYS}
            )
            for annotation in annotations
            # A damaged file has nulls and dangling references here; they are dropped like any other entry.
            if isinstance(annotation, DictionaryObject) and annotation.get("/Subtype") in PDF_ANNOTATION_SUBTYPES
        )
    _drop_metadata(page=page)

    return page


def _drop_metadata(*, page: PageObject) -> None:
    """
    XMP and an editor's private data taken off everything the cut page still reaches - its resources and
    the appearance of its annotations, all the way down. Walked rather than recursed, since a file can nest
    deep enough to exhaust the stack, and each object visited once, since forms can refer to each other.
    """
    pending = [page]
    seen = set()
    while pending:
        item = pending.pop()
        if isinstance(item, IndirectObject):
            reference = (item.idnum, item.generation)
            if reference in seen:
                continue
            seen.add(reference)
        pending.extend(_without_metadata(item=item.get_object()))


def _without_metadata(*, item: object) -> list:
    """
    What a dictionary or an array holds, the dictionary's XMP and private data taken off first. Anything
    else holds nothing to walk.
    """
    if isinstance(item, ArrayObject):
        return list(item)
    if not isinstance(item, DictionaryObject):
        return []
    for key in [key for key, value in item.items() if _is_metadata(key=key, value=value.get_object())]:
        del item[key]

    return list(item.values())


def _is_metadata(*, key: str, value: object) -> bool:
    """
    Whether a key holds XMP or an editor's private data - "PieceInfo", whose every entry carries the date it
    was last changed. Told apart by what the value is rather than by the key alone, because a font or a
    picture may be listed in the resources under any name, "/Metadata" too.
    """
    if key == "/Metadata":
        return isinstance(value, StreamObject) and value.get("/Subtype") == "/XML"
    return (
        key == "/PieceInfo"
        and isinstance(value, DictionaryObject)
        and all(
            isinstance(entry.get_object(), DictionaryObject) and "/LastModified" in entry.get_object()
            for entry in value.values()
        )
    )


def _date_and_orientation(*, exif: Image.Exif) -> Image.Exif:
    """
    A fresh EXIF block holding the two things worth keeping: which way up the picture goes, and when it was
    taken - which #16 shows.
    """
    kept = Image.Exif()
    if ExifTags.Base.Orientation in exif:
        kept[ExifTags.Base.Orientation] = exif[ExifTags.Base.Orientation]
    date_taken = exif.get_ifd(ExifTags.IFD.Exif).get(ExifTags.Base.DateTimeOriginal)
    if date_taken:
        kept.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.DateTimeOriginal] = date_taken

    return kept
