from dataclasses import replace

from apps.common.tests.html import parse, render_component
from apps.family_tree.domain.dates import DateParts
from apps.family_tree.readers.person import PhotoEntry
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.photo import PhotoFactory
from apps.family_tree.tests.factories.photo_person import PhotoPersonFactory

TAG = '<c-photo.lightbox :photos="photos" />'
LENA = PersonFactory.build(pk=7)
WEDDING = PhotoEntry(
    link=PhotoPersonFactory.build(photo=PhotoFactory.build(pk=5, description="Hochzeit am Hof"), person=LENA),
    url="/media/photos/5/original.jpg",
    alt="Hochzeit am Hof",
    date_text="um 1950",
    date_parts=DateParts(year="1950", about=True),
)
UNDATED = replace(
    WEDDING,
    link=PhotoPersonFactory.build(photo=PhotoFactory.build(pk=6), person=LENA),
    url="/media/photos/6/original.jpg",
    alt="Foto ohne Beschreibung",
    date_text="",
)


def test_lightbox_shows_each_photo_whole_with_what_and_when():
    html = render_component(tag=TAG, context={"photos": [WEDDING, UNDATED]})

    first, second = parse(html).find_all("figure")
    assert (
        first["data-show"],
        first.find("img")["src"],
        first.find("figcaption").get_text(" ", strip=True),
        second["data-show"],
        second.find("figcaption").get_text(" ", strip=True),
    ) == (
        "$photo == 0",
        "/media/photos/5/original.jpg",
        "Hochzeit am Hof Aufgenommen um 1950 · Foto 1 von 2",
        "$photo == 1",
        "Foto 2 von 2",
    )


def test_lightbox_goes_round_forward_and_back():
    html = render_component(tag=TAG, context={"photos": [WEDDING, UNDATED]})

    page = parse(html)
    assert (
        page.find("button", string="Zurück")["data-on:click"],
        page.find("button", string="Vor")["data-on:click"],
    ) == ("$photo = ($photo + 2 - 1) % 2", "$photo = ($photo + 1) % 2")


def test_lightbox_of_one_photo_has_nowhere_to_go():
    html = render_component(tag=TAG, context={"photos": [WEDDING]})

    page = parse(html)
    assert (page.find("button", string="Zurück"), page.find("button", string="Vor")) == (None, None)


def test_lightbox_closes_itself():
    html = render_component(tag=TAG, context={"photos": [WEDDING]})

    assert parse(html).find("button", string="Schließen")["data-on:click"] == "el.closest('dialog').close()"


def test_lightbox_keeps_escape_from_closing_the_card_behind_it_and_goes_round_by_arrow_keys():
    html = render_component(tag=TAG, context={"photos": [WEDDING, UNDATED]})

    assert parse(html).find(id="photo-lightbox")["data-on:keydown"] == (
        "evt.key == 'Escape' && evt.stopPropagation(); "
        "evt.key == 'ArrowLeft' && ($photo = ($photo + 2 - 1) % 2); "
        "evt.key == 'ArrowRight' && ($photo = ($photo + 1) % 2)"
    )
