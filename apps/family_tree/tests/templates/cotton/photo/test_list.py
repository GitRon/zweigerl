from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.domain.dates import DateParts
from apps.family_tree.readers.person import PhotoEntry, PhotosTab
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.photo import PhotoFactory
from apps.family_tree.tests.factories.photo_person import PhotoPersonFactory

TAG = '<c-photo.list :photos_tab="photos_tab" />'
LENA = PersonFactory.build(pk=7)
ENTRY = PhotoEntry(
    link=PhotoPersonFactory.build(photo=PhotoFactory.build(pk=5), person=LENA),
    url="/media/photos/5/original.jpg",
    alt="Foto ohne Beschreibung",
    date_text="",
    date_parts=DateParts(),
)


def test_list_shows_each_photo_and_the_lightbox():
    html = render_component(tag=TAG, context={"photos_tab": PhotosTab(person=LENA, photos=[ENTRY])})

    page = parse(html)
    assert (page.find(id="photo-5") is not None, page.find(id="photo-lightbox") is not None) == (True, True)


def test_list_without_photos_invites_the_first():
    html = render_component(tag=TAG, context={"photos_tab": PhotosTab(person=LENA, photos=[])})

    page = parse(html)
    assert ("Noch kein Foto da." in page.get_text(), page.find(id="photo-lightbox")) == (True, None)


def test_list_uploads_photos_for_the_person():
    html = render_component(tag=TAG, context={"photos_tab": PhotosTab(person=LENA, photos=[])})

    form = parse(html).find("input", attrs={"type": "file"}).find_parent("form")
    assert (form["data-on:submit"], form.find("input", attrs={"type": "file"})["accept"]) == (
        f"@post('{reverse('family_tree:photo-create-view', kwargs={'pk': 7})}', {{contentType: 'form'}})",
        ".jpg,.jpeg,.png,.webp",
    )
