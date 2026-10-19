import datetime
import io
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import ExifTags, Image

from apps.common.media import UploadRefusedError
from apps.family_tree.actions.photo import add_photos, describe_photo, set_portrait
from apps.family_tree.domain.dates import DateKind, Precision, UncertainDate
from apps.family_tree.models import Person, Photo, PhotoPerson
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.photo import PhotoFactory
from apps.family_tree.tests.factories.photo_person import PhotoPersonFactory

ABOUT_1950 = UncertainDate(kind=DateKind.ABOUT, date_1=datetime.date(1950, 1, 1), precision=Precision.YEAR)


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path) -> Path:
    settings.MEDIA_ROOT = tmp_path

    return tmp_path


def _jpeg(*, date_taken: str = "", latitude: bool = False) -> bytes:
    exif = Image.Exif()
    if date_taken:
        exif.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.DateTimeOriginal] = date_taken
    if latitude:
        exif.get_ifd(ExifTags.IFD.GPSInfo)[ExifTags.GPS.GPSLatitude] = (47.0, 46.0, 0.0)
    output = io.BytesIO()
    Image.new("RGB", (8, 6), "white").save(output, "JPEG", exif=exif)

    return output.getvalue()


@pytest.mark.django_db
def test_add_photos_stores_each_under_its_id(media_root):
    lena = PersonFactory()

    (photo,) = add_photos(person_id=lena.pk, files=[SimpleUploadedFile("Lena Huber am Hof.JPG", _jpeg())])

    assert photo.file.name == f"photos/{photo.pk}/original.jpg"
    assert (media_root / photo.file.name).exists() is True


@pytest.mark.django_db
def test_add_photos_keeps_the_date_taken_and_drops_where(media_root):
    lena = PersonFactory()

    (photo,) = add_photos(
        person_id=lena.pk,
        files=[SimpleUploadedFile("am Hof.jpg", _jpeg(date_taken="2009:07:14 16:02:11", latitude=True))],
    )

    stored = Image.open(media_root / photo.file.name).getexif()
    assert (Photo.objects.get(pk=photo.pk).date_1, stored.get_ifd(ExifTags.IFD.GPSInfo)) == (
        datetime.date(2009, 7, 14),
        {},
    )


@pytest.mark.django_db
def test_add_photos_leaves_the_date_open_without_one():
    lena = PersonFactory()

    (photo,) = add_photos(person_id=lena.pk, files=[SimpleUploadedFile("am Hof.jpg", _jpeg())])

    assert Photo.objects.get(pk=photo.pk).date is None


@pytest.mark.django_db
def test_add_photos_makes_the_first_the_portrait_of_somebody_without_one():
    lena = PersonFactory()

    first, second = add_photos(
        person_id=lena.pk, files=[SimpleUploadedFile("1.jpg", _jpeg()), SimpleUploadedFile("2.jpg", _jpeg())]
    )

    assert list(PhotoPerson.objects.filter(person=lena).values_list("photo", "is_portrait")) == [
        (first.pk, True),
        (second.pk, False),
    ]


@pytest.mark.django_db
def test_add_photos_keeps_the_portrait_somebody_has():
    portrait = PhotoPersonFactory(is_portrait=True)

    (photo,) = add_photos(person_id=portrait.person.pk, files=[SimpleUploadedFile("1.jpg", _jpeg())])

    assert PhotoPerson.objects.get(photo=photo).is_portrait is False


@pytest.mark.django_db
def test_add_photos_refuses_somebody_not_in_the_tree():
    with pytest.raises(Person.DoesNotExist, match="Person matching query does not exist"):
        add_photos(person_id=404, files=[SimpleUploadedFile("1.jpg", _jpeg())])


@pytest.mark.django_db
def test_add_photos_refuses_a_scan_before_storing_anything(media_root):
    lena = PersonFactory()

    with pytest.raises(UploadRefusedError, match="Fotos bitte als JPEG, PNG oder WebP"):
        add_photos(
            person_id=lena.pk,
            files=[SimpleUploadedFile("1.jpg", _jpeg()), SimpleUploadedFile("Taufschein.pdf", b"%PDF-1.4")],
        )

    assert list(media_root.iterdir()) == []


@pytest.mark.django_db
def test_add_photos_refused_halfway_leaves_no_row_and_no_file(media_root):
    lena = PersonFactory()

    with pytest.raises(UploadRefusedError, match="lässt sich nicht als Bild öffnen"):
        add_photos(
            person_id=lena.pk,
            files=[SimpleUploadedFile("1.jpg", _jpeg()), SimpleUploadedFile("2.jpg", b"kein Bild")],
        )

    assert (Photo.objects.count(), list((media_root / "photos").rglob("*.jpg"))) == (0, [])


@pytest.mark.django_db
def test_set_portrait_moves_it_from_the_one_before():
    before = PhotoPersonFactory(is_portrait=True)
    other = PhotoPersonFactory(person=before.person)

    set_portrait(person_id=before.person.pk, photo_id=other.photo.pk)

    assert list(PhotoPerson.objects.filter(person=before.person).values_list("pk", "is_portrait")) == [
        (before.pk, False),
        (other.pk, True),
    ]


@pytest.mark.django_db
def test_set_portrait_leaves_other_people_alone():
    gerti = PhotoPersonFactory(is_portrait=True)
    lena = PhotoPersonFactory()

    set_portrait(person_id=lena.person.pk, photo_id=lena.photo.pk)

    assert PhotoPerson.objects.get(pk=gerti.pk).is_portrait is True


@pytest.mark.django_db
def test_set_portrait_refuses_a_photo_the_person_is_not_on():
    lena = PersonFactory()
    other = PhotoPersonFactory()

    with pytest.raises(PhotoPerson.DoesNotExist, match="PhotoPerson matching query does not exist"):
        set_portrait(person_id=lena.pk, photo_id=other.photo.pk)


@pytest.mark.django_db
def test_describe_photo_saves_what_it_shows_and_when():
    link = PhotoPersonFactory()

    describe_photo(
        person_id=link.person.pk, photo_id=link.photo.pk, description="  Hochzeit am Hof  ", date=" um 1950 "
    )

    photo = Photo.objects.get(pk=link.photo.pk)
    assert (photo.description, photo.date, photo.sort_date) == (
        "Hochzeit am Hof",
        ABOUT_1950,
        datetime.date(1950, 1, 1),
    )


@pytest.mark.django_db
def test_describe_photo_can_forget_the_date():
    link = PhotoPersonFactory(photo=PhotoFactory(about_1950=True))

    describe_photo(person_id=link.person.pk, photo_id=link.photo.pk, description="", date="")

    assert Photo.objects.get(pk=link.photo.pk).date is None


@pytest.mark.django_db
def test_describe_photo_refuses_a_date_that_is_none():
    link = PhotoPersonFactory()

    with pytest.raises(ValidationError, match=r"„30\.2\.1950“ ist kein gültiges Datum"):
        describe_photo(person_id=link.person.pk, photo_id=link.photo.pk, description="Am Hof", date="30.2.1950")


@pytest.mark.django_db
def test_describe_photo_refuses_a_photo_no_longer_there():
    lena = PersonFactory()

    with pytest.raises(Photo.DoesNotExist, match="Photo matching query does not exist"):
        describe_photo(person_id=lena.pk, photo_id=404, description="", date="")


@pytest.mark.django_db
def test_describe_photo_refuses_a_photo_the_person_is_not_on():
    lena = PersonFactory()
    other = PhotoPersonFactory()

    with pytest.raises(Photo.DoesNotExist, match="Photo matching query does not exist"):
        describe_photo(person_id=lena.pk, photo_id=other.photo.pk, description="Am Hof", date="")
