from dataclasses import replace

from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import PersonListEntry
from apps.family_tree.readers.tree import TreeCard
from apps.family_tree.tests.factories.person import PersonFactory

CARD = TreeCard(
    entry=PersonListEntry(person=PersonFactory.build(pk=7), name="Gerti Huber", initials="GH", lifespan="* 1958"),
    x=164,
    y=280,
    lineage=(7, 9),
)


def test_card_shows_name_and_lifespan():
    html = render_component(
        tag='<c-tree.card :card="card" width="140" height="190" />',
        context={"card": CARD},
    )

    assert parse(html).find(id="tree-card-7").get_text(" ", strip=True) == "GH Gerti Huber * 1958"


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


def test_card_labels_an_ancestor_in_whom_two_lines_meet():
    html = render_component(
        tag='<c-tree.card :card="card" width="140" height="190" />',
        context={"card": TreeCard(entry=CARD.entry, x=CARD.x, y=CARD.y, pedigree_collapse=True)},
    )

    page = parse(html)
    assert page.find(id=page.find(id="tree-card-7")["aria-describedby"]).get_text(strip=True) == "Ahnenschwund"


def test_card_without_pedigree_collapse_has_no_label():
    html = render_component(
        tag='<c-tree.card :card="card" width="140" height="190" />',
        context={"card": CARD},
    )

    assert parse(html).find(id="tree-card-7-collapse") is None


def test_card_shows_the_portrait_in_the_frame():
    entry = replace(CARD.entry, portrait_url="/media/photos/5/original.jpg", portrait_alt="Am Hof")

    html = render_component(
        tag='<c-tree.card :card="card" width="140" height="190" />',
        context={"card": replace(CARD, entry=entry)},
    )

    image = parse(html).find(id="tree-card-7").find("img")
    assert (image["src"], image["alt"]) == ("/media/photos/5/original.jpg", "Am Hof")


def test_card_fades_unless_it_is_the_selected_person_or_one_of_their_ancestors():
    html = render_component(
        tag='<c-tree.card :card="card" width="140" height="190" />',
        context={"card": CARD},
    )

    assert "($ancestors && ![7, 9].includes($selection))" in parse(html).find(id="tree-card-7")["data-class"]
