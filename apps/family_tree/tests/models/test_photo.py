import datetime

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.family_tree.domain.dates import DateKind, Precision, UncertainDate
from apps.family_tree.models import Photo, PhotoPerson
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.photo import PhotoFactory
from apps.family_tree.tests.factories.photo_person import PhotoPersonFactory
from apps.family_tree.tests.factories.tree import TreeFactory

ABOUT_1950 = UncertainDate(kind=DateKind.ABOUT, date_1=datetime.date(1950, 1, 1), precision=Precision.YEAR)


def test_photo_str_is_its_stored_name():
    assert str(PhotoFactory.build(file="photos/7/original.jpg")) == "photos/7/original.jpg"


def test_photo_storage_name_comes_from_the_id_alone():
    assert PhotoFactory.build(pk=7).storage_name == "photos/7/original"


@pytest.mark.django_db
def test_photo_save_derives_the_sort_date():
    photo = PhotoFactory(
        date_kind="between", date_1=datetime.date(1950, 1, 1), date_2=datetime.date(1960, 1, 1), precision="year"
    )

    assert Photo.objects.get(pk=photo.pk).sort_date == datetime.date(1955, 7, 2)


@pytest.mark.django_db
def test_photo_save_of_some_fields_keeps_the_sort_date_in_step():
    photo = PhotoFactory(about_1950=True)
    photo.date_1 = datetime.date(1952, 1, 1)

    photo.save(update_fields=["date_1"])

    assert Photo.objects.get(pk=photo.pk).sort_date == datetime.date(1952, 1, 1)


@pytest.mark.django_db
def test_photo_save_leaves_a_photo_without_date_unsorted():
    photo = PhotoFactory()

    assert Photo.objects.get(pk=photo.pk).sort_date is None


def test_photo_clean_derives_the_sort_date():
    photo = PhotoFactory.build(about_1950=True)

    photo.clean()

    assert photo.sort_date == datetime.date(1950, 1, 1)


def test_photo_date_is_the_structured_date():
    assert PhotoFactory.build(about_1950=True).date == ABOUT_1950


def test_photo_date_is_none_without_one():
    assert PhotoFactory.build().date is None


def test_photo_date_is_none_for_a_range_without_its_end():
    photo = PhotoFactory.build(date_kind="between", date_1=datetime.date(1950, 1, 1), precision="year")

    assert photo.date is None


def test_photo_set_date_fills_the_fields():
    photo = PhotoFactory.build()

    photo.set_date(date=ABOUT_1950)

    assert (photo.date_kind, photo.date_1, photo.date_2, photo.precision) == (
        "about",
        datetime.date(1950, 1, 1),
        None,
        "year",
    )


def test_photo_set_date_to_none_empties_the_fields():
    photo = PhotoFactory.build(about_1950=True)

    photo.set_date(date=None)

    assert (photo.date_kind, photo.date_1, photo.date_2, photo.precision) == ("", None, None, "")


@pytest.mark.django_db
def test_photo_refuses_a_date_without_its_precision_on_save():
    with pytest.raises(ValidationError, match="Ein Aufnahmedatum braucht seine Art und seine Genauigkeit"):
        PhotoFactory(date_kind="exact", date_1=datetime.date(1950, 1, 1))


@pytest.mark.django_db
def test_photo_refuses_a_date_without_its_precision_in_the_database():
    with pytest.raises(IntegrityError, match="photo_date_complete"):
        Photo.objects.bulk_create(
            [
                Photo(
                    tree=TreeFactory(),
                    date_kind="exact",
                    date_1=datetime.date(1950, 1, 1),
                    sort_date=datetime.date(1950, 1, 1),
                )
            ]
        )


@pytest.mark.django_db
def test_photo_refuses_a_date_without_its_sort_date_in_the_database():
    with pytest.raises(IntegrityError, match="photo_sort_date_with_date"):
        Photo.objects.bulk_create(
            [Photo(tree=TreeFactory(), date_kind="exact", date_1=datetime.date(1950, 1, 1), precision="year")]
        )


@pytest.mark.django_db
def test_photo_refuses_a_second_date_that_is_no_range_on_save():
    with pytest.raises(ValidationError, match="Ein zweites Datum gibt es nur bei „zwischen“"):
        PhotoFactory(about_1950=True, date_2=datetime.date(1960, 1, 1))


@pytest.mark.django_db
def test_photo_refuses_a_second_date_that_is_no_range_in_the_database():
    with pytest.raises(IntegrityError, match="photo_date_2_only_between"):
        Photo.objects.bulk_create(
            [
                Photo(
                    tree=TreeFactory(),
                    date_kind="about",
                    date_1=datetime.date(1950, 1, 1),
                    date_2=datetime.date(1960, 1, 1),
                    precision="year",
                    sort_date=datetime.date(1950, 1, 1),
                )
            ]
        )


def test_photo_person_str_names_the_person_and_the_photo():
    link = PhotoPersonFactory.build(
        person=PersonFactory.build(given_names="Lena", surname="Huber"),
        photo=PhotoFactory.build(file="photos/7/original.jpg"),
    )

    assert str(link) == "Lena Huber auf photos/7/original.jpg"


@pytest.mark.django_db
def test_photo_person_refuses_the_same_person_twice_on_save():
    link = PhotoPersonFactory()

    with pytest.raises(ValidationError, match="Diese Person ist auf dem Foto schon eingetragen"):
        PhotoPersonFactory(photo=link.photo, person=link.person)


@pytest.mark.django_db
def test_photo_person_refuses_the_same_person_twice_in_the_database():
    link = PhotoPersonFactory()

    with pytest.raises(IntegrityError, match=r"photo_id, family_tree_photoperson\.person_id"):
        PhotoPerson.objects.bulk_create([PhotoPerson(photo=link.photo, person=link.person)])


@pytest.mark.django_db
def test_photo_person_refuses_a_second_portrait_on_save():
    portrait = PhotoPersonFactory(is_portrait=True)

    with pytest.raises(ValidationError, match="Eine Person hat höchstens ein Titelbild"):
        PhotoPersonFactory(person=portrait.person, is_portrait=True)


@pytest.mark.django_db
def test_photo_person_refuses_a_second_portrait_in_the_database():
    portrait = PhotoPersonFactory(is_portrait=True)

    with pytest.raises(IntegrityError, match=r"family_tree_photoperson\.person_id"):
        PhotoPerson.objects.bulk_create([PhotoPerson(photo=PhotoFactory(), person=portrait.person, is_portrait=True)])


@pytest.mark.django_db
def test_photo_person_allows_many_photos_that_are_no_portrait():
    first = PhotoPersonFactory()

    second = PhotoPersonFactory(person=first.person)

    assert list(first.person.photos.all()) == [first.photo, second.photo]


@pytest.mark.django_db
def test_photo_person_refuses_a_person_of_another_tree():
    photo = PhotoFactory()

    with pytest.raises(ValidationError, match="Das Foto und die Person gehören zu verschiedenen Stammbäumen"):
        PhotoPersonFactory(photo=photo, person=PersonFactory(tree__name="Familie Berger"))
