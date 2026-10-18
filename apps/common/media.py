"""
Storing a photo or a scan: the one way an upload reaches the media directory.

See docs/patterns/data-storage.md, "Photos and scans".
"""

import io
import uuid
from pathlib import PurePosixPath

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from PIL import ExifTags, Image, ImageOps, UnidentifiedImageError

# The extension a file is stored under, and the Pillow format its content has to have. PDFs are not images
# and are checked by their signature instead.
IMAGE_FORMATS = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP", "tif": "TIFF", "tiff": "TIFF"}
PDF_EXTENSION = "pdf"
PDF_SIGNATURE = b"%PDF-"

# What a picture tells about the camera and the place, rather than about the picture. The date it was taken
# is not among them: it stays, and #16 shows it.
CAMERA_TAGS_IN_MAIN_IFD = (
    ExifTags.Base.Make,
    ExifTags.Base.Model,
    ExifTags.Base.Software,
    ExifTags.Base.HostComputer,
)
CAMERA_TAGS_IN_EXIF_IFD = (
    ExifTags.Base.MakerNote,
    ExifTags.Base.BodySerialNumber,
    ExifTags.Base.CameraOwnerName,
    ExifTags.Base.LensMake,
    ExifTags.Base.LensModel,
    ExifTags.Base.LensSerialNumber,
    ExifTags.Base.LensSpecification,
)


class UploadRefusedError(ValueError):
    """
    The file is not one Zweigerl keeps. The message is meant for the person who uploaded it.
    """


def store_upload(*, uploaded_file: UploadedFile, folder: str) -> str:
    """
    Stores a photo or a scan in "MEDIA_ROOT/<folder>/" under a random name and returns the stored name, as a
    FileField wants it. The original name is dropped: it often says who is in the picture. Images lose their
    GPS and camera data on the way; PDFs are stored as they came.
    """
    extension = PurePosixPath(uploaded_file.name or "").suffix.lstrip(".").lower()
    content = uploaded_file.read()

    if extension in IMAGE_FORMATS:
        content = _without_location_and_camera(content=content, expected_format=IMAGE_FORMATS[extension])
    elif extension == PDF_EXTENSION:
        if not content.startswith(PDF_SIGNATURE):
            raise UploadRefusedError("Die Datei endet auf .pdf, ist aber kein PDF.")
    else:
        raise UploadRefusedError("Zweigerl nimmt Fotos und Scans als JPEG, PNG, WebP, TIFF oder PDF.")

    return default_storage.save(f"{folder}/{uuid.uuid4().hex}.{extension}", ContentFile(content))


def _without_location_and_camera(*, content: bytes, expected_format: str) -> bytes:
    """
    The image saved again without the GPS block and the camera tags. JPEG keeps its quantisation tables
    ("quality='keep'"), so the picture is not visibly recompressed.
    """
    try:
        image = Image.open(io.BytesIO(content))
        image.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as error:
        raise UploadRefusedError("Die Datei lässt sich nicht als Bild öffnen.") from error
    if image.format != expected_format:
        raise UploadRefusedError("Die Dateiendung passt nicht zum Inhalt des Bildes.")

    exif = image.getexif()
    if ExifTags.IFD.GPSInfo in exif:
        del exif[ExifTags.IFD.GPSInfo]
    for tag in CAMERA_TAGS_IN_MAIN_IFD:
        exif.pop(tag, None)
    exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
    for tag in CAMERA_TAGS_IN_EXIF_IFD:
        exif_ifd.pop(tag, None)

    options = {"exif": exif, "icc_profile": image.info.get("icc_profile")}
    if expected_format == "JPEG":
        options["quality"] = "keep"
    elif expected_format == "TIFF":
        # Pillow writes no EXIF sub-blocks into a TIFF, so the orientation would be lost and a scan could
        # come back on its side. It is applied to the pixels instead, and the date taken does not survive
        # here - a scan rarely carries one.
        image = ImageOps.exif_transpose(image)
        options = {"icc_profile": image.info.get("icc_profile")}

    output = io.BytesIO()
    image.save(output, expected_format, **options)
    return output.getvalue()
