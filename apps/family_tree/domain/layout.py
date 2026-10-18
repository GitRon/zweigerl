"""
The layout of the tree (#11): people and how they are related in, where every card and every line goes out.
The rules are docs/patterns/tree-layout.md.

Pure: no database, no Django. "readers.tree" loads the rows and calls "layout".
"""

import datetime
import math
import zlib
from collections import defaultdict, deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from statistics import fmean

from apps.family_tree.domain.stroke import Segment, pen_stroke

# Sizes in pixels. The cards' own look is #12's; these only say how much room each one takes.
CARD_WIDTH = 140
CARD_HEIGHT = 190
PARTNER_GAP = 24
SIBLING_GAP = 32
BLOCK_GAP = 64
ROW_GAP = 90
# How much higher than a couple's the bar of a single parent's children runs, so a father's son from before the
# marriage does not look like the couple's.
BAR_STEP = 15

# How often the rows are reordered and placed, down the tree and back up. Each pass moves parents over their
# children and children under their parents; a handful settles any tree a family has.
SWEEPS = 4


@dataclass(frozen=True, kw_only=True)
class LayoutPerson:
    id: int
    # The sort date of their birth (#5), which orders siblings. Without one a person goes to the end.
    birth: datetime.date | None = None


@dataclass(frozen=True, kw_only=True)
class PartnerLink:
    person_a: int
    person_b: int


@dataclass(frozen=True, kw_only=True)
class ParentLink:
    parent: int
    child: int


@dataclass(frozen=True, kw_only=True)
class SiblingLink:
    """
    Two siblings whose shared parents nobody knows - a SiblingPair.
    """

    person_a: int
    person_b: int


@dataclass(frozen=True, kw_only=True)
class Card:
    person_id: int
    # The top left corner.
    x: int
    y: int
    # 0 is the home person's row, -1 their parents', 1 their children's.
    generation: int


@dataclass(frozen=True, kw_only=True)
class Placeholder:
    """
    Where the unknown parents of siblings only a SiblingPair connects would stand: drawn with a dashed frame,
    a gap in the research rather than a person.
    """

    sibling_ids: tuple[int, ...]
    x: int
    y: int
    generation: int


class LineKind(StrEnum):
    PARTNERS = "partners"
    CHILDREN = "children"


@dataclass(frozen=True, kw_only=True)
class Line:
    kind: LineKind
    # An SVG path, see "domain.stroke".
    path: str


@dataclass(frozen=True, kw_only=True)
class TreeLayout:
    cards: tuple[Card, ...] = ()
    placeholders: tuple[Placeholder, ...] = ()
    lines: tuple[Line, ...] = ()
    width: int = 0
    height: int = 0


def layout(
    *,
    people: Sequence[LayoutPerson],
    partnerships: Sequence[PartnerLink],
    parent_links: Sequence[ParentLink],
    sibling_links: Sequence[SiblingLink],
    home_person_id: int | None,
) -> TreeLayout:
    """
    The tree around the home person: everyone connected to them, in rows by generation. Who is not connected
    is left out - they are the loose twigs of #19. Every input in a stable order, the order of their rows, so
    the same tree comes out the same way every time.
    """
    graph = _Graph.build(
        people=people, partnerships=partnerships, parent_links=parent_links, sibling_links=sibling_links
    )
    if home_person_id not in graph.birth:
        return TreeLayout()

    tree = _Tree(graph=graph, generations=_generations(graph=graph, home_person_id=home_person_id))
    tree.arrange()
    return tree.result()


@dataclass(kw_only=True)
class _Graph:
    birth: dict[int, datetime.date | None]
    partnerships: list[tuple[int, int]]
    parents: defaultdict[int, list[int]] = field(default_factory=lambda: defaultdict(list))
    children: defaultdict[int, list[int]] = field(default_factory=lambda: defaultdict(list))
    partners: defaultdict[int, list[int]] = field(default_factory=lambda: defaultdict(list))
    siblings: defaultdict[int, list[int]] = field(default_factory=lambda: defaultdict(list))

    @classmethod
    def build(
        cls,
        *,
        people: Sequence[LayoutPerson],
        partnerships: Sequence[PartnerLink],
        parent_links: Sequence[ParentLink],
        sibling_links: Sequence[SiblingLink],
    ) -> _Graph:
        graph = cls(
            birth={person.id: person.birth for person in people},
            partnerships=[(link.person_a, link.person_b) for link in partnerships],
        )
        for person_a, person_b in graph.partnerships:
            graph.partners[person_a].append(person_b)
            graph.partners[person_b].append(person_a)
        for link in parent_links:
            graph.parents[link.child].append(link.parent)
            graph.children[link.parent].append(link.child)
        for link in sibling_links:
            graph.siblings[link.person_a].append(link.person_b)
            graph.siblings[link.person_b].append(link.person_a)
        return graph

    def sibling_order(self, *, person_id: int) -> tuple[bool, datetime.date, int]:
        """
        Siblings by birth, those without a birth date at the end, ties in the order they were entered.
        """
        birth = self.birth[person_id]
        return (birth is None, birth or datetime.date.min, person_id)


def _generations(*, graph: _Graph, home_person_id: int) -> dict[int, int]:
    """
    Everyone connected to the home person with their generation, nearest first: a parent is one above, a child
    one below, a partner and a sibling in the same row. Where two paths disagree - a marriage across
    generations - the shorter wins; drawing that properly is #31's.
    """
    generations = {home_person_id: 0}
    queue = deque([home_person_id])
    while queue:
        person_id = queue.popleft()
        steps = (
            [(parent, -1) for parent in graph.parents[person_id]]
            + [(child, 1) for child in graph.children[person_id]]
            + [(other, 0) for other in graph.partners[person_id] + graph.siblings[person_id]]
        )
        for other, step in steps:
            if other not in generations:
                generations[other] = generations[person_id] + step
                queue.append(other)
    return generations


@dataclass(kw_only=True, eq=False)
class _Family:
    """
    Children and the parents they share. A child with one known parent is a family of one parent, so
    half-siblings hang from the parent they share until #31 puts them under the right couple. The parent of
    siblings only a SiblingPair connects is a placeholder, whose node is a negative number.
    """

    parents: tuple[int, ...]
    children: list[int]
    # The seed of its line: what stays the same while the tree around it changes.
    key: str


@dataclass(kw_only=True, eq=False)
class _Unit:
    """
    What stands in a row as one: a couple, a single person or a placeholder - the nodes left to right.
    """

    nodes: list[int]
    generation: int
    # Whether the two are a Partnership and get the line between them, rather than two parents of one child.
    partnership: bool = False
    x: float = 0.0

    @property
    def width(self) -> int:
        return len(self.nodes) * CARD_WIDTH + (len(self.nodes) - 1) * PARTNER_GAP

    @property
    def center(self) -> float:
        return self.x + self.width / 2


@dataclass(kw_only=True, eq=False)
class _Block:
    """
    The units that stay together in a row, in a fixed order: siblings and their partners, or one unit with no
    parents in the tree.
    """

    family: _Family | None
    units: list[_Unit]


class _Tree:
    def __init__(self, *, graph: _Graph, generations: dict[int, int]) -> None:
        self.graph = graph
        self.generations = dict(generations)
        # Discovery order from the home person, which the rows start out in.
        self.discovered = {node: index for index, node in enumerate(generations)}
        self.families = self._families()
        self.family_of = {child: family for family in self.families for child in family.children}
        self.families_of: dict[int, list[_Family]] = defaultdict(list)
        for family in self.families:
            for parent in family.parents:
                self.families_of[parent].append(family)
        self.units = self._units()
        self.unit_of = {node: unit for unit in self.units for node in unit.nodes}
        self.rows = self._rows()

    # --- Structure -----------------------------------------------------------------------------------------

    def _families(self) -> list[_Family]:
        by_parents: dict[tuple[int, ...], list[int]] = {}
        for person_id in self.generations:
            parents = tuple(sorted(self.graph.parents[person_id]))
            if parents:
                by_parents.setdefault(parents, []).append(person_id)
        families = [
            _Family(parents=parents, children=children, key="children-" + "-".join(map(str, parents)))
            for parents, children in by_parents.items()
        ]
        families.extend(self._placeholder_families())
        for family in families:
            family.children.sort(key=lambda child: self.graph.sibling_order(person_id=child))
        return families

    def _placeholder_families(self) -> list[_Family]:
        """
        Siblings without known parents, held together by SiblingPairs, hang from one placeholder per group.
        """
        families = []
        grouped: set[int] = set()
        for person_id in list(self.generations):
            if person_id in grouped or not self._without_parents(person_id=person_id):
                continue
            group = self._sibling_group(person_id=person_id)
            grouped.update(group)
            if len(group) > 1:
                placeholder = -(len(families) + 1)
                self.generations[placeholder] = self.generations[person_id] - 1
                self.discovered[placeholder] = self.discovered[person_id] - 0.5
                families.append(
                    _Family(parents=(placeholder,), children=group, key="placeholder-" + "-".join(map(str, group)))
                )
        return families

    def _without_parents(self, *, person_id: int) -> bool:
        return not self.graph.parents[person_id]

    def _sibling_group(self, *, person_id: int) -> list[int]:
        group = [person_id]
        for member in group:
            for sibling in self.graph.siblings[member]:
                if sibling not in group and self._without_parents(person_id=sibling):
                    group.append(sibling)
        return sorted(group)

    def _units(self) -> list[_Unit]:
        """
        Couples first, as their Partnerships were entered, then two parents of one child; one partner per
        person, the others are #31's. Everyone left stands alone.
        """
        paired: set[int] = set()
        units = []
        candidates = [(pair, True) for pair in self.graph.partnerships] + [
            (family.parents, False) for family in self.families if len(family.parents) == 2
        ]
        for (person_a, person_b), partnership in candidates:
            if self._can_pair(person_a=person_a, person_b=person_b, paired=paired):
                paired.update((person_a, person_b))
                units.append(
                    _Unit(
                        nodes=self._couple_order(person_a=person_a, person_b=person_b),
                        generation=self.generations[person_a],
                        partnership=partnership,
                    )
                )
        units.extend(
            _Unit(nodes=[node], generation=generation)
            for node, generation in self.generations.items()
            if node not in paired
        )
        return units

    def _can_pair(self, *, person_a: int, person_b: int, paired: set[int]) -> bool:
        return (
            person_a in self.generations
            and person_b in self.generations
            and person_a not in paired
            and person_b not in paired
            and self.generations[person_a] == self.generations[person_b]
        )

    def _couple_order(self, *, person_a: int, person_b: int) -> list[int]:
        """
        The one whose siblings the couple stands among comes first: the one with parents in the tree, or the
        one nearer to the home person.
        """
        return sorted((person_a, person_b), key=lambda node: (node not in self.family_of, self.discovered[node]))

    def _rows(self) -> list[list[_Block]]:
        blocks: dict[tuple[int, int], _Block] = {}
        for unit in sorted(self.units, key=lambda unit: self.discovered[unit.nodes[0]]):
            family = self.family_of.get(unit.nodes[0])
            key = (id(family) if family else id(unit), unit.generation)
            blocks.setdefault(key, _Block(family=family, units=[])).units.append(unit)
        for block in blocks.values():
            if block.family:
                block.units.sort(key=lambda unit: self.graph.sibling_order(person_id=unit.nodes[0]))

        rows: dict[int, list[_Block]] = defaultdict(list)
        for block in blocks.values():
            rows[block.units[0].generation].append(block)
        return [rows[generation] for generation in sorted(rows)]

    # --- Placement -----------------------------------------------------------------------------------------

    def center(self, *, node: int) -> float:
        unit = self.unit_of[node]
        return unit.x + unit.nodes.index(node) * (CARD_WIDTH + PARTNER_GAP) + CARD_WIDTH / 2

    def anchor(self, *, family: _Family) -> float:
        """
        Where the line to the children leaves the parents: the middle between them.
        """
        return fmean(self.center(node=parent) for parent in family.parents)

    def arrange(self) -> None:
        for row in self.rows:
            _place(row=row, desired={})
        for _ in range(SWEEPS):
            for row in self.rows[1:]:
                self._sweep_down(row=row)
            for row in reversed(self.rows[:-1]):
                self._sweep_up(row=row)

    def _sweep_down(self, *, row: list[_Block]) -> None:
        """
        Children under their parents: each block of siblings in the order of their parents above, centred
        under them.
        """
        for block in row:
            for unit in block.units:
                self._face_partner_family(unit=unit)
        row.sort(key=lambda block: self.anchor(family=block.family) if block.family else _center(block=block))

        desired = {}
        for block in row:
            if block.family is None:
                continue
            offset = self.anchor(family=block.family) - _packed_width(units=block.units) / 2
            for unit in block.units:
                desired[unit] = offset + unit.width / 2
                offset += unit.width + SIBLING_GAP
        _place(row=row, desired=desired)

    def _face_partner_family(self, *, unit: _Unit) -> None:
        """
        A couple whose both halves have parents in the tree turns so each stands on the side of their own.
        """
        if len(unit.nodes) != 2:
            return
        first, second = unit.nodes
        own, partners = self.family_of.get(first), self.family_of.get(second)
        if own and partners and own is not partners:
            unit.nodes = [first, second] if self.anchor(family=own) <= self.anchor(family=partners) else [second, first]

    def _sweep_up(self, *, row: list[_Block]) -> None:
        """
        Parents over their children: each unit over the middle of its children below, the blocks in that order.
        """
        desired = {}
        for block in row:
            for unit in block.units:
                children = [
                    self.center(node=child)
                    for node in unit.nodes
                    for family in self.families_of.get(node, [])
                    for child in family.children
                ]
                if children:
                    desired[unit] = fmean(children)
        row.sort(key=lambda block: fmean(desired.get(unit, unit.center) for unit in block.units))
        _place(row=row, desired=desired)

    # --- Result --------------------------------------------------------------------------------------------

    def result(self) -> TreeLayout:
        left = min(unit.x for unit in self.units)
        top = self.rows[0][0].units[0].generation
        corners = {
            node: (
                _pixel(value=self.center(node=node) - CARD_WIDTH / 2 - left),
                (self.generations[node] - top) * (CARD_HEIGHT + ROW_GAP),
            )
            for node in self.unit_of
        }
        cards = tuple(
            Card(person_id=node, x=x, y=y, generation=self.generations[node])
            for node, (x, y) in sorted(corners.items(), key=lambda item: (item[1][1], item[1][0]))
            if node > 0
        )
        placeholders = tuple(
            Placeholder(
                sibling_ids=tuple(family.children),
                x=corners[family.parents[0]][0],
                y=corners[family.parents[0]][1],
                generation=self.generations[family.parents[0]],
            )
            for family in self.families
            if family.parents[0] < 0
        )
        return TreeLayout(
            cards=cards,
            placeholders=placeholders,
            lines=self._partner_lines(corners=corners) + self._children_lines(corners=corners),
            width=max(x for x, _ in corners.values()) + CARD_WIDTH,
            height=len(self.rows) * (CARD_HEIGHT + ROW_GAP) - ROW_GAP,
        )

    def _partner_lines(self, *, corners: dict[int, tuple[int, int]]) -> tuple[Line, ...]:
        lines = []
        for unit in self.units:
            if unit.partnership:
                (left_x, y), (right_x, _) = corners[unit.nodes[0]], corners[unit.nodes[1]]
                middle = y + CARD_HEIGHT / 2
                lines.append(
                    Line(
                        kind=LineKind.PARTNERS,
                        path=pen_stroke(
                            segments=[((left_x + CARD_WIDTH, middle), (right_x, middle))],
                            seed=_seed(key="partners-" + "-".join(map(str, sorted(unit.nodes)))),
                        ),
                    )
                )
        return tuple(lines)

    def _children_lines(self, *, corners: dict[int, tuple[int, int]]) -> tuple[Line, ...]:
        """
        From the parents down to a bar above the children, and from the bar down to each child. A couple's
        line leaves the middle of the line between them, anyone else's the bottom of their cards, with its bar a
        step higher.
        """
        lines = []
        for family in self.families:
            anchor_x = fmean(corners[parent][0] + CARD_WIDTH / 2 for parent in family.parents)
            unit = self.unit_of[family.parents[0]]
            children = [(corners[child][0] + CARD_WIDTH / 2, corners[child][1]) for child in family.children]
            bar_y = min(y for _, y in children) - ROW_GAP / 2
            if unit.partnership and set(family.parents) == set(unit.nodes):
                start_y = corners[family.parents[0]][1] + CARD_HEIGHT / 2
            else:
                start_y = max(corners[parent][1] for parent in family.parents) + CARD_HEIGHT
                bar_y -= BAR_STEP
            bar = sorted({anchor_x, *(x for x, _ in children)})

            segments: list[Segment] = [((anchor_x, start_y), (anchor_x, bar_y))]
            if len(bar) > 1:
                segments.append(((bar[0], bar_y), (bar[-1], bar_y)))
            segments.extend(((x, bar_y), (x, y)) for x, y in children)
            lines.append(Line(kind=LineKind.CHILDREN, path=pen_stroke(segments=segments, seed=_seed(key=family.key))))
        return tuple(lines)


def _place(*, row: list[_Block], desired: dict[_Unit, float]) -> None:
    """
    Sets every unit's x as close to the centre it wants as the row allows: in the row's order, never closer to
    its neighbour than the gap. A unit that wants nothing stays where it is. Least squares under these
    constraints is an isotonic regression, solved by pooling adjacent violators.
    """
    units = [unit for block in row for unit in block.units]
    gaps = [SIBLING_GAP if same_block else BLOCK_GAP for same_block in _same_block_pairs(row=row)]
    offsets = [0.0]
    for unit, gap in zip(units[:-1], gaps, strict=True):
        offsets.append(offsets[-1] + unit.width + gap)
    targets = [
        desired.get(unit, unit.center) - unit.width / 2 - offset for unit, offset in zip(units, offsets, strict=True)
    ]

    pools: list[list[float]] = []
    for target in targets:
        pools.append([target, 1])
        while len(pools) > 1 and pools[-2][0] / pools[-2][1] > pools[-1][0] / pools[-1][1]:
            total, count = pools.pop()
            pools[-1][0] += total
            pools[-1][1] += count
    positions = [total / count for total, count in pools for _ in range(int(count))]
    for unit, position, offset in zip(units, positions, offsets, strict=True):
        unit.x = position + offset


def _same_block_pairs(*, row: list[_Block]) -> list[bool]:
    """
    For each pair of neighbouring units in the row: whether the two belong to the same block.
    """
    pairs = []
    for index, block in enumerate(row):
        pairs.extend([True] * (len(block.units) - 1))
        if index < len(row) - 1:
            pairs.append(False)
    return pairs


def _packed_width(*, units: list[_Unit]) -> float:
    return sum(unit.width for unit in units) + SIBLING_GAP * (len(units) - 1)


def _center(*, block: _Block) -> float:
    return fmean(unit.center for unit in block.units)


def _pixel(*, value: float) -> int:
    # Rounds half up everywhere, so two cards a whole number of pixels apart stay exactly that far apart.
    return math.floor(value + 0.5)


def _seed(*, key: str) -> int:
    # crc32, not hash(): Python salts the hash of a string per process, so a line would change on every restart.
    return zlib.crc32(key.encode())
