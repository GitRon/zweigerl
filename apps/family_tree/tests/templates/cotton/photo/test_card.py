from dataclasses import replace

from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import PhotoEntry
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.photo import PhotoFactory
from apps.family_tree.tests.factories.photo_person import PhotoPersonFactory

TAG = '<c-photo.card :entry="entry" :person="person" :index="index" />'
LENA = PersonFactory.build(pk=7)
ENTRY = PhotoEntry(
    link=PhotoPersonFactory.build(photo=PhotoFactory.build(pk=5, description="Hochzeit am Hof"), person=LENA),
    url="/media/photos/5/original.jpg",
    alt="Hochzeit am Hof",
    date="um 1950",
)
UNDESCRIBED = replace(
    ENTRY,
    link=PhotoPersonFactory.build(photo=PhotoFactory.build(pk=5), person=LENA, is_portrait=True),
    alt="Foto ohne Beschreibung",
    date="",
)


def test_card_shows_the_photo_with_what_it_shows_and_when():
    html = render_component(tag=TAG, context={"entry": ENTRY, "person": LENA, "index": 2})

    card = parse(html).find(id="photo-5")
    assert (
        card.find("img")["src"],
        card.find("img")["alt"],
        "Hochzeit am Hof" in card.get_text(),
        "Aufgenommen um 1950" in card.get_text(),
    ) == ("/media/photos/5/original.jpg", "Hochzeit am Hof", True, True)


def test_card_opens_the_lightbox_at_the_photo():
    html = render_component(tag=TAG, context={"entry": ENTRY, "person": LENA, "index": 2})

    button = parse(html).find("button", attrs={"aria-haspopup": "dialog"})
    assert (button["aria-label"], button["data-on:click"]) == (
        "Groß ansehen: Hochzeit am Hof",
        "$photo = 2; document.getElementById('photo-lightbox').showModal()",
    )


def test_card_makes_a_photo_the_portrait():
    html = render_component(tag=TAG, context={"entry": ENTRY, "person": LENA, "index": 0})

    url = reverse("family_tree:photo-portrait-view", kwargs={"pk": 7, "photo_pk": 5})
    form = parse(html).find("button", string="Als Titelbild").find_parent("form")
    assert form["data-on:submit"] == f"@post('{url}', {{contentType: 'form'}})"


def test_card_labels_the_portrait_instead():
    html = render_component(tag=TAG, context={"entry": UNDESCRIBED, "person": LENA, "index": 0})

    page = parse(html)
    assert ("Titelbild" in page.get_text(), page.find("button", string="Als Titelbild")) == (True, None)


def test_card_says_what_is_not_known_yet():
    html = render_component(tag=TAG, context={"entry": UNDESCRIBED, "person": LENA, "index": 0})

    text = parse(html).get_text()
    assert ("Noch ohne Beschreibung." in text, "Wann aufgenommen, weiß noch niemand." in text) == (True, True)


def test_card_describes_the_photo_filled_in():
    html = render_component(tag=TAG, context={"entry": ENTRY, "person": LENA, "index": 0})

    url = reverse("family_tree:photo-describe-view", kwargs={"pk": 7, "photo_pk": 5})
    form = parse(html).find("textarea", attrs={"name": "description"}).find_parent("form")
    assert (
        form["data-on:submit"],
        form.find("textarea").get_text(),
        form.find("input", attrs={"name": "date"})["value"],
    ) == (
        f"@post('{url}', {{contentType: 'form'}})",
        "Hochzeit am Hof",
        "um 1950",
    )
