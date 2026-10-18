from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import PersonListEntry
from apps.family_tree.tests.factories.person import PersonFactory

ENTRY = PersonListEntry(person=PersonFactory.build(pk=7), name="Gerti Huber", initials="GH", lifespan="1958 –")


def test_card_shows_name_and_lifespan():
    html = render_component(tag='<c-person.card :entry="entry" />', context={"entry": ENTRY})

    assert parse(html).find("h2").get_text() == "Gerti Huber" and "1958 –" in parse(html).get_text()


def test_card_shows_while_the_person_is_selected():
    html = render_component(tag='<c-person.card :entry="entry" />', context={"entry": ENTRY})

    assert parse(html).find(id="person-card")["data-show"] == "$selection == 7"


def test_card_closes_by_clearing_the_selection():
    html = render_component(tag='<c-person.card :entry="entry" />', context={"entry": ENTRY})

    assert parse(html).find("button")["data-on:click"] == "$selection = 0"
