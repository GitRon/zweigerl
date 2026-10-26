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
from apps.family_tree.models import Fact, ParentChild, Partnership, Person, SiblingPair
from apps.family_tree.readers.person import PersonListEntry, person_entries
from apps.family_tree.readers.trees import home_person


@dataclass(frozen=True, kw_only=True)
class TreeCard:
    entry: PersonListEntry
    # The top left corner, see "domain.layout.Card".
    x: int
    y: int
    # An ancestor in whom two lines of the home person meet - Ahnenschwund (#31).
    pedigree_collapse: bool = False
    # Whose line of ancestors the card is part of: the person themselves and their descendants (#103).
    lineage: tuple[int, ...] = ()


@dataclass(frozen=True, kw_only=True)
class Tree:
    cards: list[TreeCard]
    placeholders: tuple[Placeholder, ...]
    lines: tuple[Line, ...]
    width: int
    height: int
    card_width: int = CARD_WIDTH
    card_height: int = CARD_HEIGHT

    @property
    def person_ids(self) -> list[int]:
        """
        Everyone the tree shows: only for them does a line of ancestors stand out.
        """
        return [card.entry.person.pk for card in self.cards]


def tree(*, tree_id: int) -> Tree:
    """
    The tree "tree_id" as the canvas draws it (#12): the layout of "tree_layout", each card with the name, initials and
    Lebensdaten of its person, whether two of the home person's lines meet in them and whose line of ancestors
    they are part of.
    """
    laid_out = tree_layout(tree_id=tree_id)
    entries = person_entries(person_ids=[card.person_id for card in laid_out.cards])

    return Tree(
        cards=[
            TreeCard(
                entry=entries[card.person_id],
                x=card.x,
                y=card.y,
                pedigree_collapse=card.pedigree_collapse,
                lineage=laid_out.lineages[card.person_id],
            )
            for card in laid_out.cards
        ],
        placeholders=laid_out.placeholders,
        lines=laid_out.lines,
        width=laid_out.width,
        height=laid_out.height,
    )


def tree_card(*, pk: int) -> TreeCard | None:
    """
    The one card of the person "pk" in their tree, to patch it after their name changed (#30) - or None for
    somebody the tree does not show.
    """
    tree_id = Person.objects.filter(pk=pk).values_list("tree", flat=True).first()
    if tree_id is None:
        return None
    return next((card for card in tree(tree_id=tree_id).cards if card.entry.person.pk == pk), None)


def tree_layout(*, tree_id: int) -> TreeLayout:
    """
    The whole tree "tree_id", laid out around the home person - or, while nobody has been chosen, around the person
    entered first. A person with several birth facts is sorted among their siblings by the earliest. See
    docs/patterns/tree-layout.md.
    """
    people = [
        LayoutPerson(id=person_id, birth=birth)
        for person_id, birth in Person.objects.filter(tree=tree_id)
        .annotate(birth=Min("facts__sort_date", filter=Q(facts__kind=Fact.Kind.BIRTH)))
        .order_by("pk")
        .values_list("pk", "birth")
    ]
    chosen = home_person(tree_id=tree_id)

    return layout(
        people=people,
        partnerships=[
            PartnerLink(person_a=person_a, person_b=person_b)
            for person_a, person_b in Partnership.objects.filter(person_a__tree=tree_id)
            .order_by("pk")
            .values_list("person_a", "person_b")
        ],
        parent_links=[
            ParentLink(parent=parent, child=child)
            for parent, child in ParentChild.objects.filter(child__tree=tree_id)
            .order_by("pk")
            .values_list("parent", "child")
        ],
        sibling_links=[
            SiblingLink(person_a=person_a, person_b=person_b)
            for person_a, person_b in SiblingPair.objects.filter(person_a__tree=tree_id)
            .order_by("pk")
            .values_list("person_a", "person_b")
        ],
        home_person_id=chosen.pk if chosen else (people[0].id if people else None),
    )
