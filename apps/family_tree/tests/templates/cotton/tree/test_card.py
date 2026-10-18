from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import PersonListEntry
from apps.family_tree.readers.tree import TreeCard
from apps.family_tree.tests.factories.person import PersonFactory

CARD = TreeCard(
    entry=PersonListEntry(person=PersonFactory.build(pk=7), name="Gerti Huber", initials="GH", lifespan="1958 –"),
    x=164,
    y=280,
)


def test_card_shows_name_and_lifespan():
    html = render_component(
        tag='<c-tree.card :card="card" width="140" height="190" />',
        context={"card": CARD},
    )

    assert parse(html).find(id="tree-card-7").get_text(" ", strip=True) == "GH Gerti Huber 1958 –"


def test_card_selects_the_person_and_fetches_their_person_card():
    html = render_component(
        tag='<c-tree.card :card="card" width="140" height="190" />',
        context={"card": CARD},
    )

    assert (
        parse(html).find(id="tree-card-7")["data-on:click"]
        == f"$selection = 7; @get('{reverse('family_tree:person-view', kwargs={'pk': 7})}')"
    )


def test_card_tells_assistive_technology_whether_it_is_selected():
    html = render_component(
        tag='<c-tree.card :card="card" width="140" height="190" />',
        context={"card": CARD},
    )

    assert parse(html).find(id="tree-card-7")["data-attr:aria-pressed"] == "String($selection == 7)"
