from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import PersonListEntry
from apps.family_tree.tests.factories.person import PersonFactory

TAG = '<c-person.portrait :entry="entry" />'


def test_portrait_shows_the_photo():
    entry = PersonListEntry(
        person=PersonFactory.build(pk=7),
        name="Gerti Huber",
        initials="GH",
        lifespan="—",
        portrait_url="/media/photos/5/original.jpg",
        portrait_alt="Am Hof",
    )

    html = render_component(tag=TAG, context={"entry": entry})

    image = parse(html).find(id="person-card-portrait").find("img")
    assert (image["src"], image["alt"]) == ("/media/photos/5/original.jpg", "Am Hof")


def test_portrait_without_a_photo_shows_the_initials():
    entry = PersonListEntry(person=PersonFactory.build(pk=7), name="Gerti Huber", initials="GH", lifespan="—")

    html = render_component(tag=TAG, context={"entry": entry})

    assert parse(html).find(id="person-card-portrait").get_text(strip=True) == "GH"
