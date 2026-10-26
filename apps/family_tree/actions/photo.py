from collections.abc import Iterable
from pathlib import PurePosixPath

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from PIL import ExifTags, Image

from apps.common.media import UploadRefusedError, delete_on_commit, store_upload
from apps.family_tree.domain.dates import UncertainDate, from_exif, from_german
from apps.family_tree.models import Person, Photo, PhotoPerson

# What a browser shows in an <img>. "store_upload" takes TIFF and PDF too, but those are scans and belong to
# a source (#15): no browser but Safari draws a TIFF.
PHOTO_EXTENSIONS = ("jpg", "jpeg", "png", "webp")


def add_photos(*, person_id: int, files: Iterable[UploadedFile]) -> list[Photo]:
    """
    Adds photos of the person (#16), each with the date the camera wrote into it, if any. The first photo of
    somebody without a portrait becomes it. Raises "Person.DoesNotExist" for somebody no longer in the tree and
    "UploadRefusedError" for a file that is no photo Zweigerl keeps - then adding none of them.
    """
    files = list(files)
    for uploaded_file in files:
        if PurePosixPath(uploaded_file.name or "").suffix.lstrip(".").lower() not in PHOTO_EXTENSIONS:
            raise UploadRefusedError("Fotos bitte als JPEG, PNG oder WebP. Ein Scan als TIFF passt zu den Quellen.")

    stored = []
    try:
        with transaction.atomic():
            person = Person.objects.get(pk=person_id)
            has_portrait = person.photo_links.filter(is_portrait=True).exists()
            for uploaded_file in files:
                # The row comes first, so its id can name the file; see docs/patterns/data-storage.md.
                photo = Photo.objects.create(tree_id=person.tree_id)
                photo.file.name = store_upload(uploaded_file=uploaded_file, name=photo.storage_name)
                stored.append(photo)
                photo.set_date(date=_date_taken(name=photo.file.name))
                photo.save()
                PhotoPerson.objects.create(photo=photo, person=person, is_portrait=not has_portrait)
                has_portrait = True
    except Exception:
        # The rows went with the transaction; the files already written go with them.
        for photo in stored:
            default_storage.delete(photo.file.name)
        raise

    return stored


def delete_photo(*, photo_id: int) -> Photo:
    """
    Deletes a photo with its file, the file once the deletion is committed (#72). Only the admin does: a person
    deleted from the tree leaves their photos, as their sources, and the admin is where they are found then;
    see docs/patterns/data-storage.md, "When a file goes". Raises "Photo.DoesNotExist" for a photo already gone.
    """
    with transaction.atomic():
        photo = Photo.objects.get(pk=photo_id)
        photo.delete()
        delete_on_commit(names=[photo.file.name])

    return photo


def set_portrait(*, person_id: int, photo_id: int) -> PhotoPerson:
    """
    Makes one of the person's photos their portrait, the one before it an ordinary photo again. Raises
    "PhotoPerson.DoesNotExist" for a photo the person is not on.
    """
    with transaction.atomic():
        link = PhotoPerson.objects.get(person_id=person_id, photo_id=photo_id)
        PhotoPerson.objects.filter(person_id=person_id, is_portrait=True).exclude(pk=link.pk).update(is_portrait=False)
        link.is_portrait = True
        link.save(update_fields=["is_portrait"])

    return link


def describe_photo(*, person_id: int, photo_id: int, description: str, date: str) -> Photo:
    """
    Says what a photo of the person shows and when it was taken - "date" is German free text such as "um 1950",
    read by "domain.dates.from_german", and empty while nobody knows. Raises "Photo.DoesNotExist" for a photo
    no longer there or one the person is not on, and "ValidationError" for a date that is none.
    """
    photo = Photo.objects.get(pk=photo_id, people=person_id)
    photo.description = description.strip()
    try:
        photo.set_date(date=from_german(text=date) if date.strip() else None)
    except ValueError as error:
        raise ValidationError(str(error)) from error
    photo.save()

    return photo


def _date_taken(*, name: str) -> UncertainDate | None:
    # "store_upload" kept the date taken and nothing else of the EXIF block (#21).
    with default_storage.open(name) as stored_file, Image.open(stored_file) as image:
        text = image.getexif().get_ifd(ExifTags.IFD.Exif).get(ExifTags.Base.DateTimeOriginal)
    return from_exif(text=text) if isinstance(text, str) else None
