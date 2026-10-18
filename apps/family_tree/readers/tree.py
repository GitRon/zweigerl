from dataclasses import dataclass

from django.db.models import Min, Q

from apps.family_tree.domain.layout import (
    CARD_HEIGHT,
    CARD_WIDTH,
    LayoutPerson,
    Line,
    ParentLink,
    PartnerLink,
    Placeholder,
    SiblingLink,
    TreeLayout,
    layout,
)
from apps.family_tree.models import Fact, ParentChild, Partnership, Person, SiblingPair, TreeSettings
from apps.family_tree.readers.person import PersonListEntry, person_entries


@dataclass(frozen=True, kw_only=True)
class TreeCard:
    entry: PersonListEntry
    # The top left corner, see "domain.layout.Card".
    x: int
    y: int


@dataclass(frozen=True, kw_only=True)
class Tree:
    cards: list[TreeCard]
    placeholders: tuple[Placeholder, ...]
    lines: tuple[Line, ...]
    width: int
    height: int
    card_width: int = CARD_WIDTH
    card_height: int = CARD_HEIGHT


def tree() -> Tree:
    """
    The tree as the canvas draws it (#12): the layout of "tree_layout", each card with the name, initials and
    Lebensdaten of its person.
    """
    laid_out = tree_layout()
    entries = person_entries(person_ids=[card.person_id for card in laid_out.cards])

    return Tree(
        cards=[TreeCard(entry=entries[card.person_id], x=card.x, y=card.y) for card in laid_out.cards],
        placeholders=laid_out.placeholders,
        lines=laid_out.lines,
        width=laid_out.width,
        height=laid_out.height,
    )


def tree_layout() -> TreeLayout:
    """
    The whole tree, laid out around the home person - or, while nobody has been chosen, around the person
    entered first. A person with several birth facts is sorted among their siblings by the earliest. See
    docs/patterns/tree-layout.md.
    """
    people = [
        LayoutPerson(id=person_id, birth=birth)
        for person_id, birth in Person.objects.annotate(
            birth=Min("facts__sort_date", filter=Q(facts__kind=Fact.Kind.BIRTH))
        )
        .order_by("pk")
        .values_list("pk", "birth")
    ]
    chosen = TreeSettings.objects.filter(pk=TreeSettings.ONLY_ROW).values_list("home_person_id", flat=True).first()

    return layout(
        people=people,
        partnerships=[
            PartnerLink(person_a=person_a, person_b=person_b)
            for person_a, person_b in Partnership.objects.order_by("pk").values_list("person_a", "person_b")
        ],
        parent_links=[
            ParentLink(parent=parent, child=child)
            for parent, child in ParentChild.objects.order_by("pk").values_list("parent", "child")
        ],
        sibling_links=[
            SiblingLink(person_a=person_a, person_b=person_b)
            for person_a, person_b in SiblingPair.objects.order_by("pk").values_list("person_a", "person_b")
        ],
        home_person_id=chosen or (people[0].id if people else None),
    )
