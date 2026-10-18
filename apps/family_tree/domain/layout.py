"""
The layout of the tree (#11): people and how they are related in, where every card and every line goes out.
The rules are docs/patterns/tree-layout.md.

Pure: no database, no Django. "readers.tree" loads the rows and calls "layout".
"""

import datetime
import heapq
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
# How much lower the line to a partner runs for every card it passes behind, so the line to a third spouse does
# not lie on the line to the second.
PARTNER_STEP = 12

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
    # An ancestor in whom two of the home person's lines meet, see "_pedigree_collapse".
    pedigree_collapse: bool = False


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
    return tree.result(pedigree_collapse=_pedigree_collapse(graph=graph, home_person_id=home_person_id))


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

    def couples(self) -> list[tuple[int, int]]:
        """
        Who should stand side by side: the Partnerships as they were entered, then two parents of one child.
        """
        co_parents = {tuple(sorted(parents)) for parents in self.parents.values() if len(parents) == 2}
        return self.partnerships + sorted(co_parents)

    def steps(self, *, person_id: int) -> list[tuple[int, int, bool]]:
        """
        Everyone one step from a person: the other, the change of generation, and whether the step is a weak one -
        to a partner or a sibling rather than a parent or a child.
        """
        return (
            [(parent, -1, False) for parent in self.parents[person_id]]
            + [(child, 1, False) for child in self.children[person_id]]
            + [(other, 0, True) for other in self.partners[person_id] + self.siblings[person_id]]
        )

    def sibling_order(self, *, person_id: int) -> tuple[bool, datetime.date, int]:
        """
        Siblings by birth, those without a birth date at the end, ties in the order they were entered.
        """
        birth = self.birth[person_id]
        return (birth is None, birth or datetime.date.min, person_id)


def _generations(*, graph: _Graph, home_person_id: int) -> dict[int, int]:
    """
    Everyone connected to the home person with their generation, in the order they are reached from them: a
    parent one row above, a child one below, a partner and a sibling in the same row. Where two paths disagree,
    "_nearest_generations" picks one, and "_parents_above_children" and "_partners_together" settle what is left.
    """
    order = {home_person_id: None}
    queue = deque([home_person_id])
    while queue:
        for other, _, _ in graph.steps(person_id=queue.popleft()):
            if other not in order:
                order[other] = None
                queue.append(other)

    nearest = _nearest_generations(graph=graph, home_person_id=home_person_id)
    generations = {person_id: nearest[person_id] for person_id in order}
    _parents_above_children(graph=graph, generations=generations)
    _partners_together(graph=graph, generations=generations, home_person_id=home_person_id)
    return generations


def _nearest_generations(*, graph: _Graph, home_person_id: int) -> dict[int, int]:
    """
    The generation along the path with the fewest steps to partners and siblings, then the shortest - blood
    before marriage, so a niece who married her uncle stays a row below her father.
    """
    best = {home_person_id: (0, 0, 0)}
    heap = [(0, 0, 0, home_person_id)]
    while heap:
        weak, strong, generation, person_id = heapq.heappop(heap)
        if best[person_id] != (weak, strong, generation):
            continue
        for other, step, is_weak in graph.steps(person_id=person_id):
            cost = (weak + is_weak, strong + (not is_weak))
            if other not in best or cost < best[other][:2]:
                best[other] = (*cost, generation + step)
                heapq.heappush(heap, (*cost, generation + step, other))
    return {person_id: generation for person_id, (_, _, generation) in best.items()}


def _parents_above_children(*, graph: _Graph, generations: dict[int, int]) -> None:
    """
    A parent stands above their child even where paths of different length disagree - pedigree collapse over a
    different number of generations: above the home person's row the parent moves up, below it the child moves
    down, and the line between them crosses the rows in between. A cycle of parents, which only wrong data has,
    stops after as many rounds as there are people.
    """
    for _ in generations:
        if not _move_parents_above_children(graph=graph, generations=generations):
            return


def _move_parents_above_children(*, graph: _Graph, generations: dict[int, int]) -> bool:
    """
    One round of "_parents_above_children": whether anybody moved.
    """
    moved = False
    links = [(above, below) for above in generations for below in graph.children[above]]
    for parent, child in links:
        if generations[parent] >= generations[child]:
            moved = True
            if generations[child] <= 0:
                generations[parent] = generations[child] - 1
            else:
                generations[child] = generations[parent] + 1
    return moved


def _partners_together(*, graph: _Graph, generations: dict[int, int], home_person_id: int) -> None:
    """
    A couple in two rows moves into one wherever every parent can still stand above their child: the one further
    from the home person moves, else the other. The home person stays where they are. A couple that cannot - a
    marriage across generations - keeps its two rows and gets a stepped line.
    """
    for person_a, person_b in graph.couples():
        if person_a not in generations or generations[person_a] == generations[person_b]:
            continue
        moves = sorted(
            ((person_a, generations[person_b]), (person_b, generations[person_a])),
            key=lambda move: -abs(generations[move[0]]),
        )
        for person_id, generation in moves:
            if person_id != home_person_id and _fits(
                graph=graph, generations=generations, person_id=person_id, generation=generation
            ):
                generations[person_id] = generation
                break


def _fits(*, graph: _Graph, generations: dict[int, int], person_id: int, generation: int) -> bool:
    return all(generations[parent] < generation for parent in graph.parents[person_id]) and all(
        generations[child] > generation for child in graph.children[person_id]
    )


def _pedigree_collapse(*, graph: _Graph, home_person_id: int) -> set[int]:
    """
    The ancestors of the home person in whom two of their lines meet - Ahnenschwund: two or more of their children
    are the home person or among the home person's ancestors, as the grandparents a cousin and a cousin who
    married share. Their own ancestors are reached the same two ways but are not marked; the mark is where the
    lines join.
    """
    line = {home_person_id}
    queue = deque([home_person_id])
    while queue:
        for parent in graph.parents[queue.popleft()]:
            if parent not in line:
                line.add(parent)
                queue.append(parent)
    return {
        person_id
        for person_id in line - {home_person_id}
        if sum(child in line for child in graph.children[person_id]) > 1
    }


@dataclass(kw_only=True, eq=False)
class _Family:
    """
    Children and the parents they share. Half-siblings belong to different families - the couple of each, or
    the one parent who is known - and so hang from different lines. The parent of siblings only a SiblingPair
    connects is a placeholder, whose node is a negative number.
    """

    parents: tuple[int, ...]
    children: list[int]
    # The seed of its line: what stays the same while the tree around it changes.
    key: str


@dataclass(kw_only=True, eq=False)
class _Couple:
    """
    Two who stand side by side in a unit. "near" is the one nearer the middle of the unit; the line to the
    children leaves the gap on the inner side of "far".
    """

    near: int
    far: int
    # Whether the two are a Partnership and get the line between them, rather than two parents of one child.
    partnership: bool


@dataclass(kw_only=True, eq=False)
class _Unit:
    """
    What stands in a row as one: a person with their partners, a single person or a placeholder - the nodes
    left to right.
    """

    nodes: list[int]
    generation: int
    # The one whose siblings the unit stands among: the one with parents in the tree, or the nearest.
    root: int
    couples: list[_Couple] = field(default_factory=list)
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
        self.couple_of = {
            frozenset((couple.near, couple.far)): couple for unit in self.units for couple in unit.couples
        }
        # Partnerships whose two stand in different rows - a marriage across generations - with a stepped line.
        self.across = {
            frozenset(pair): pair
            for pair in graph.partnerships
            if pair[0] in self.generations and self.generations[pair[0]] != self.generations[pair[1]]
        }
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
        Everyone joined by couples in their row stands as one unit: whoever has the most partners in the middle,
        the first of them to the left and the others to the right, so the children of each couple hang under
        their own pair. Everyone left stands alone.
        """
        partners_of: defaultdict[int, list[tuple[int, bool]]] = defaultdict(list)
        partnerships = set(map(frozenset, self.graph.partnerships))
        seen: set[frozenset[int]] = set()
        for person_a, person_b in self.graph.couples():
            pair = frozenset((person_a, person_b))
            if pair not in seen and self._same_row(person_a=person_a, person_b=person_b):
                seen.add(pair)
                partners_of[person_a].append((person_b, pair in partnerships))
                partners_of[person_b].append((person_a, pair in partnerships))

        units = []
        placed: set[int] = set()
        for node, generation in self.generations.items():
            if node in placed:
                continue
            nodes, hub = self._line_up(node=node, partners_of=partners_of)
            placed.update(nodes)
            units.append(
                _Unit(
                    nodes=nodes,
                    generation=generation,
                    root=min(nodes, key=lambda member: (member not in self.family_of, self.discovered[member])),
                    couples=_couples(nodes=nodes, middle=nodes.index(hub), partners_of=partners_of),
                )
            )
        return units

    def _same_row(self, *, person_a: int, person_b: int) -> bool:
        return (
            person_a in self.generations
            and person_b in self.generations
            and self.generations[person_a] == self.generations[person_b]
        )

    def _line_up(self, *, node: int, partners_of: dict[int, list[tuple[int, bool]]]) -> tuple[list[int], int]:
        """
        Everyone joined to a node by couples, left to right, and the hub among them: who has the most partners -
        of a single couple the one with parents in the tree, or the nearer. Whoever has partners of their own
        takes them further out on their side.
        """
        component = [node]
        for member in component:
            component.extend(partner for partner, _ in partners_of[member] if partner not in component)
        hub = min(
            component,
            key=lambda member: (-len(partners_of[member]), member not in self.family_of, self.discovered[member]),
        )

        nodes = [hub]
        hub_partners = [partner for partner, _ in partners_of[hub]]
        queue = deque((partner, index == 0 and len(hub_partners) > 1) for index, partner in enumerate(hub_partners))
        while queue:
            person_id, left = queue.popleft()
            if person_id in nodes:
                continue
            if left:
                nodes.insert(0, person_id)
            else:
                nodes.append(person_id)
            queue.extend((partner, left) for partner, _ in partners_of[person_id])
        return nodes, hub

    def _rows(self) -> list[list[_Block]]:
        blocks: dict[tuple[int, int], _Block] = {}
        for unit in sorted(self.units, key=lambda unit: self.discovered[unit.root]):
            family = self.family_of.get(unit.root)
            key = (id(family) if family else id(unit), unit.generation)
            blocks.setdefault(key, _Block(family=family, units=[])).units.append(unit)
        for block in blocks.values():
            if block.family:
                block.units.sort(key=lambda unit: self.graph.sibling_order(person_id=unit.root))

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
        Where the line to the children leaves the parents: the gap on the inner side of the outer of a couple -
        between the two when they stand side by side - or else the middle between the parents.
        """
        couple = self.couple_of.get(frozenset(family.parents))
        if couple:
            return (self.center(node=couple.far) + self.center(node=self._inner(couple=couple))) / 2
        return fmean(self.center(node=parent) for parent in family.parents)

    def _inner(self, *, couple: _Couple) -> int:
        """
        The card next to the outer of a couple, on the side of the other: the other themselves when the two
        stand side by side.
        """
        nodes = self.unit_of[couple.far].nodes
        far, near = nodes.index(couple.far), nodes.index(couple.near)
        return nodes[far - 1 if far > near else far + 1]

    def _drop(self, *, couple: _Couple) -> float:
        """
        How far below the top of the cards the line between a couple runs: half the card, and a step lower for
        every card it passes behind.
        """
        nodes = self.unit_of[couple.far].nodes
        return CARD_HEIGHT / 2 + (abs(nodes.index(couple.far) - nodes.index(couple.near)) - 1) * PARTNER_STEP

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

    def result(self, *, pedigree_collapse: set[int]) -> TreeLayout:
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
            Card(
                person_id=node,
                x=x,
                y=y,
                generation=self.generations[node],
                pedigree_collapse=node in pedigree_collapse,
            )
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
        """
        Between the facing edges of a couple in one row, a step lower for every card it passes behind; across
        rows, out of the upper one's side, down between them and into the lower one's side.
        """
        lines = []
        for unit in self.units:
            for couple in unit.couples:
                if couple.partnership:
                    left_node, right_node = sorted((couple.near, couple.far), key=unit.nodes.index)
                    y = corners[left_node][1] + self._drop(couple=couple)
                    segments = [((corners[left_node][0] + CARD_WIDTH, y), (corners[right_node][0], y))]
                    lines.append(_partner_line(pair=(couple.near, couple.far), segments=segments))
        lines.extend(
            _partner_line(pair=pair, segments=_across_rows(corners=corners, pair=pair)) for pair in self.across.values()
        )
        return tuple(lines)

    def _children_lines(self, *, corners: dict[int, tuple[int, int]]) -> tuple[Line, ...]:
        """
        From the parents down to a bar above the children, and from the bar down to each child. A couple's
        line leaves the line between them, anyone else's the bottom of their cards; "_bar_shift" says how high
        the bar runs.
        """
        lines = []
        for family in self.families:
            children = [(corners[child][0] + CARD_WIDTH / 2, corners[child][1]) for child in family.children]
            (anchor_x, start_y), from_partner_line = self._line_start(family=family, corners=corners)
            bar_y = (
                min(y for _, y in children)
                - ROW_GAP / 2
                + self._bar_shift(family=family, from_partner_line=from_partner_line)
            )
            bar = sorted({anchor_x, *(x for x, _ in children)})

            segments: list[Segment] = [((anchor_x, start_y), (anchor_x, bar_y))]
            if len(bar) > 1:
                segments.append(((bar[0], bar_y), (bar[-1], bar_y)))
            segments.extend(((x, bar_y), (x, y)) for x, y in children)
            lines.append(Line(kind=LineKind.CHILDREN, path=pen_stroke(segments=segments, seed=_seed(key=family.key))))
        return tuple(lines)

    def _bar_shift(self, *, family: _Family, from_partner_line: bool) -> float:
        """
        How far a family's bar runs from halfway between the rows: a step higher where the line does not leave
        a partner line, and for every further couple of the same unit a step lower - at most two - so the bars
        of half-siblings never run together into one.
        """
        couple = self.couple_of.get(frozenset(family.parents))
        order = self.unit_of[couple.far].couples.index(couple) if couple else 0
        return min(order, 2) * BAR_STEP - (0 if from_partner_line else BAR_STEP)

    def _line_start(self, *, family: _Family, corners: dict[int, tuple[int, int]]) -> tuple[tuple[float, float], bool]:
        """
        Where the line to a family's children starts, and whether that is on the line between its parents: in
        the gap beside the outer of a couple, on the upright of a stepped line, or below the parents' cards.
        """
        parents = frozenset(family.parents)
        bottom = max(corners[parent][1] for parent in family.parents) + CARD_HEIGHT
        if couple := self.couple_of.get(parents):
            x = (corners[couple.far][0] + corners[self._inner(couple=couple)][0]) / 2 + CARD_WIDTH / 2
            if couple.partnership:
                return (x, corners[couple.far][1] + self._drop(couple=couple)), True
            return (x, bottom), False
        if pair := self.across.get(parents):
            return _across_rows(corners=corners, pair=pair)[-1][0], True
        return (fmean(corners[parent][0] + CARD_WIDTH / 2 for parent in family.parents), bottom), False


def _couples(*, nodes: list[int], middle: int, partners_of: dict[int, list[tuple[int, bool]]]) -> list[_Couple]:
    """
    Every couple in a unit once, the one nearer the middle - the hub - as "near".
    """
    couples = []
    for index, person_id in enumerate(nodes):
        for partner, partnership in partners_of[person_id]:
            other = nodes.index(partner)
            if (abs(index - middle), index) < (abs(other - middle), other):
                couples.append(_Couple(near=person_id, far=partner, partnership=partnership))
    return couples


def _across_rows(*, corners: dict[int, tuple[int, int]], pair: tuple[int, int]) -> list[Segment]:
    """
    The stepped line of a couple in two rows, kept clear of other cards: out of the upper one's side facing the
    lower, down the gap beside them, across above the lower row, down the gap beside the lower one and into
    their side. The children of the two hang from its last bend.
    """
    upper, lower = sorted(pair, key=lambda node: corners[node][1])
    (upper_x, upper_y), (lower_x, lower_y) = corners[upper], corners[lower]
    if lower_x >= upper_x:
        start_x, end_x, side = upper_x + CARD_WIDTH, lower_x, PARTNER_GAP / 2
    else:
        start_x, end_x, side = upper_x, lower_x + CARD_WIDTH, -PARTNER_GAP / 2
    out_x, in_x = start_x + side, end_x - side
    start_y, across_y, end_y = upper_y + CARD_HEIGHT / 2, lower_y - ROW_GAP / 4, lower_y + CARD_HEIGHT / 2
    return [
        ((start_x, start_y), (out_x, start_y)),
        ((out_x, start_y), (out_x, across_y)),
        ((out_x, across_y), (in_x, across_y)),
        ((in_x, across_y), (in_x, end_y)),
        ((in_x, end_y), (end_x, end_y)),
    ]


def _partner_line(*, pair: tuple[int, int], segments: list[Segment]) -> Line:
    return Line(
        kind=LineKind.PARTNERS,
        path=pen_stroke(segments=segments, seed=_seed(key="partners-" + "-".join(map(str, sorted(pair))))),
    )


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
