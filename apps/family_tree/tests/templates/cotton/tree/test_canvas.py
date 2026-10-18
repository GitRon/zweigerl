from apps.common.tests.html import parse, render_component
from apps.family_tree.domain.layout import Line, LineKind, Placeholder
from apps.family_tree.readers.person import PersonListEntry
from apps.family_tree.readers.tree import Tree, TreeCard
from apps.family_tree.tests.factories.person import PersonFactory

TREE = Tree(
    cards=[
        TreeCard(
            entry=PersonListEntry(person=PersonFactory.build(pk=7), name="Gerti Huber", initials="GH", lifespan="—"),
            x=0,
            y=280,
        )
    ],
    placeholders=(Placeholder(sibling_ids=(7, 8), x=0, y=0, generation=-1),),
    lines=(Line(kind=LineKind.CHILDREN, path="M 70 190 L 70 280"),),
    width=140,
    height=470,
)


def test_canvas_starts_unzoomed_with_nobody_selected():
    html = render_component(tag='<c-tree.canvas :tree="tree" />', context={"tree": TREE})

    assert parse(html).find("section")["data-signals"] == "{zoom: 1, selection: 0, filtered: false, matches: []}"


def test_canvas_draws_cards_lines_and_unknown_parents():
    html = render_component(tag='<c-tree.canvas :tree="tree" />', context={"tree": TREE})

    page = parse(html)
    assert (page.find(id="tree-card-7") is not None, page.find("path")["d"], "Eltern unbekannt" in page.get_text()) == (
        True,
        "M 70 190 L 70 280",
        True,
    )


def test_canvas_zooms_in_and_out_with_its_buttons():
    html = render_component(tag='<c-tree.canvas :tree="tree" />', context={"tree": TREE})

    page = parse(html)
    assert (
        page.find(attrs={"aria-label": "Verkleinern"})["data-on:click"],
        page.find(attrs={"aria-label": "Vergrößern"})["data-on:click"],
    ) == ("$zoom = Math.max(0.25, $zoom - 0.25)", "$zoom = Math.min(2, $zoom + 0.25)")


def test_canvas_puts_its_slot_in_the_toolbar():
    html = render_component(
        tag='<c-tree.canvas :tree="tree"><span id="extra">Abmelden</span></c-tree.canvas>', context={"tree": TREE}
    )

    assert parse(html).find(id="extra").get_text() == "Abmelden"


def test_canvas_of_an_empty_tree_invites():
    html = render_component(
        tag='<c-tree.canvas :tree="tree" />',
        context={"tree": Tree(cards=[], placeholders=(), lines=(), width=0, height=0)},
    )

    assert "Hier wachst bald dein Baum." in parse(html).get_text()
