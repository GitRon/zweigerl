from apps.common.tests.html import parse, render_component
from apps.family_tree.domain.layout import Line, LineKind, Placeholder, Stroke
from apps.family_tree.readers.person import PersonListEntry
from apps.family_tree.readers.tree import Tree, TreeCard
from apps.family_tree.tests.factories.person import PersonFactory

TREE = Tree(
    cards=[
        TreeCard(
            entry=PersonListEntry(person=PersonFactory.build(pk=7), name="Gerti Huber", initials="GH", lifespan=""),
            x=0,
            y=280,
            lineage=(7,),
        )
    ],
    placeholders=(Placeholder(sibling_ids=(7, 8), x=0, y=0, generation=-1, lineage=(7, 8)),),
    lines=(Line(kind=LineKind.CHILDREN, strokes=(Stroke(path="M 70 190 L 70 280", lineage=(7,)),)),),
    width=140,
    height=470,
)


def test_canvas_starts_unzoomed_with_nobody_selected():
    html = render_component(tag='<c-tree.canvas :tree="tree" />', context={"tree": TREE})

    assert (
        parse(html).find("section")["data-signals"]
        == "{zoom: 1, selection: 0, focus: 0, filtered: false, matches: [], ancestry: true}"
    )


def test_canvas_opens_with_the_person_selected_and_focused_whose_card_is_open():
    html = render_component(tag='<c-tree.canvas :tree="tree" selection="7" />', context={"tree": TREE})

    assert (
        parse(html).find("section")["data-signals"]
        == "{zoom: 1, selection: 7, focus: 7, filtered: false, matches: [], ancestry: true}"
    )


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


def test_canvas_lets_the_line_of_ancestors_of_the_selected_person_stand_out_and_switches_it():
    html = render_component(tag='<c-tree.canvas :tree="tree" />', context={"tree": TREE})

    page = parse(html)
    toggle = page.find(lambda tag: tag.name == "button" and "Vorfahren hervorheben" in tag.get_text())
    assert (
        page.find("section")["data-computed:ancestors"],
        toggle["data-on:click"],
        toggle["data-attr:aria-pressed"],
    ) == ("$ancestry && !$filtered && [7].includes($selection)", "$ancestry = !$ancestry", "String($ancestry)")


def test_canvas_fades_every_stroke_outside_the_line_of_ancestors_and_draws_the_line_stronger():
    html = render_component(tag='<c-tree.canvas :tree="tree" />', context={"tree": TREE})

    assert parse(html).find("path")["data-class"] == (
        "{'opacity-35': $ancestors && ![7].includes($selection), "
        "'stroke-[2.5px]': $ancestors && [7].includes($selection)}"
    )
