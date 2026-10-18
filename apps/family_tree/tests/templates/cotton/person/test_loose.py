from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import PersonListEntry
from apps.family_tree.tests.factories.person import PersonFactory

ROSA = PersonListEntry(person=PersonFactory.build(pk=9), name="Rosa Auer", initials="RA", lifespan="—")
TAG = '<c-person.loose :loose_people="loose_people" />'


def test_loose_lists_each_twig_with_a_link_to_their_card():
    section = parse(render_component(tag=TAG, context={"loose_people": [ROSA]})).find(id="loose-people")

    assert (
        "Lose Zweigerl" in section.get_text(),
        section.find("a")["href"],
        "Rosa Auer" in section.find("a").get_text(),
    ) == (True, reverse("family_tree:person-view", kwargs={"pk": 9}), True)


def test_loose_without_twigs_shows_nothing():
    assert parse(render_component(tag=TAG, context={"loose_people": []})).find(id="loose-people") is None
