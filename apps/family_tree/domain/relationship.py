"""
The German name of how someone is related to the home person, as decided in #9 - see docs/patterns/family.md.

Pure functions: no database, no Django. readers.relationship.family_graph() loads the "FamilyGraph" once, so a list
names every one of its rows from that one load.
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Self

# Person.sex holds GEDCOM's SEX. "X" (divers) and "U" (unbekannt) take the neutral word.
MALE = "M"
FEMALE = "F"

FALLBACK = "verwandt"
SAME_PERSON = "Ausgangsperson"

# A person's id, or the parent nobody knows that the members of an explicit sibling group share - the group itself.
type Node = int | frozenset[int]


@dataclass(frozen=True, kw_only=True)
class FamilyGraph:
    """
    Who is whose parent and partner, by id. "neighbours" joins everyone to their parents, children and partners
    in both directions, so whether two people are connected at all is one walk.
    """

    sex: Mapping[int, str]
    parents: Mapping[Node, frozenset[Node]]
    partners: Mapping[int, frozenset[int]]
    marriages: frozenset[frozenset[int]]
    neighbours: Mapping[Node, frozenset[Node]]

    @classmethod
    def from_links(
        cls,
        *,
        sex: Mapping[int, str],
        parent_child: Iterable[tuple[int, int]],
        partnerships: Iterable[tuple[int, int, bool]],
        sibling_pairs: Iterable[tuple[int, int]],
    ) -> Self:
        """
        Builds the graph from the rows: "parent_child" as (parent, child), "partnerships" as (a, b, married) and
        "sibling_pairs" as (a, b). Explicit siblings are siblings of each other's siblings too, and each such
        group gets one unknown shared parent, so their children are cousins like any others.
        """
        parents: defaultdict[Node, set[Node]] = defaultdict(set)
        partners: defaultdict[int, set[int]] = defaultdict(set)
        neighbours: defaultdict[Node, set[Node]] = defaultdict(set)
        marriages = set()

        links = [*parent_child]
        for group in _sibling_groups(sibling_pairs=sibling_pairs):
            links.extend((group, member) for member in group)
        for parent, child in links:
            parents[child].add(parent)
            neighbours[child].add(parent)
            neighbours[parent].add(child)

        for person_a, person_b, married in partnerships:
            partners[person_a].add(person_b)
            partners[person_b].add(person_a)
            neighbours[person_a].add(person_b)
            neighbours[person_b].add(person_a)
            if married:
                marriages.add(frozenset((person_a, person_b)))

        return cls(
            sex=sex,
            parents=_frozen(mapping=parents),
            partners=_frozen(mapping=partners),
            marriages=frozenset(marriages),
            neighbours=_frozen(mapping=neighbours),
        )


def relationship_name(*, family: FamilyGraph, home_id: int, person_id: int) -> str | None:
    """
    What "person_id" is to "home_id", in German and by the person's sex: "Urgroßvater", "Großnichte",
    "Schwägerin", "Cousine 2. Grades". Blood comes first, through the nearest common ancestor; then the partner,
    then the relatives by marriage. "verwandt" when the two are connected but no word fits, None when they are
    not connected at all.
    """
    if person_id == home_id:
        return SAME_PERSON
    sex = family.sex.get(person_id)

    distance = _blood_distance(family=family, from_id=home_id, to_id=person_id)
    blood_name = _blood_name(distance=distance, sex=sex) if distance else None
    if blood_name:
        return blood_name

    if person_id in family.partners.get(home_id, ()):
        return _partner_name(sex=sex, married=frozenset((home_id, person_id)) in family.marriages)

    in_law_name = _in_law_name(family=family, home_id=home_id, person_id=person_id)
    if in_law_name:
        return in_law_name

    return FALLBACK if _connected(family=family, from_id=home_id, to_id=person_id) else None


def _sibling_groups(*, sibling_pairs: Iterable[tuple[int, int]]) -> list[frozenset[int]]:
    """
    The explicit sibling pairs joined into groups: whoever is a sibling of one member is a sibling of all.
    """
    groups: list[frozenset[int]] = []
    for person_a, person_b in sibling_pairs:
        touching = [group for group in groups if person_a in group or person_b in group]
        groups = [group for group in groups if group not in touching]
        groups.append(frozenset((person_a, person_b)).union(*touching))
    return groups


def _frozen[K](*, mapping: Mapping[K, set]) -> dict[K, frozenset]:
    return {key: frozenset(values) for key, values in mapping.items()}


def _ancestors(*, family: FamilyGraph, person_id: int) -> dict[Node, int]:
    """
    Everyone "person_id" descends from, with the fewest generations up to them - the person themself at 0.
    """
    generations: dict[Node, int] = {person_id: 0}
    frontier: list[Node] = [person_id]
    while frontier:
        next_frontier = []
        for node in frontier:
            for parent in family.parents.get(node, ()):
                if parent not in generations:
                    generations[parent] = generations[node] + 1
                    next_frontier.append(parent)
        frontier = next_frontier
    return generations


def _blood_distance(*, family: FamilyGraph, from_id: int, to_id: int) -> tuple[int, int] | None:
    """
    The generations from each of the two up to their nearest common ancestor, or None if they have none.
    """
    up = _ancestors(family=family, person_id=from_id)
    down = _ancestors(family=family, person_id=to_id)
    common = up.keys() & down.keys()
    if not common:
        return None
    return min(((up[node], down[node]) for node in common), key=lambda pair: (sum(pair), pair))


def _gendered(*, sex: str | None, male: str, female: str, neutral: str | None = None) -> str:
    if sex == MALE:
        return male
    if sex == FEMALE:
        return female
    return neutral or f"{male} oder {female}"


def _degree_prefix(*, generations: int) -> str:
    """
    "" for the nearest generation, then "groß", "urgroß", "ururgroß": Onkel, Großonkel, Urgroßonkel.
    """
    return "ur" * (generations - 1) + "groß" if generations else ""


def _blood_name(*, distance: tuple[int, int], sex: str | None) -> str | None:
    """
    The word for a blood relative "up" generations above the common ancestor on the home person's side and
    "down" on the other's, or None for cousins of different generations, which German has no settled word for.
    """
    up, down = distance
    if down == 0:
        prefix = _degree_prefix(generations=up - 1)
        return _gendered(
            sex=sex, male=f"{prefix}vater", female=f"{prefix}mutter", neutral=f"{prefix}elternteil"
        ).capitalize()
    if up == 0:
        if down == 1:
            return _gendered(sex=sex, male="Sohn", female="Tochter", neutral="Kind")
        prefix = "ur" * (down - 2)
        return _gendered(
            sex=sex, male=f"{prefix}enkel", female=f"{prefix}enkelin", neutral=f"{prefix}enkelkind"
        ).capitalize()
    if up == 1 and down == 1:
        return _gendered(sex=sex, male="Bruder", female="Schwester", neutral="Geschwister")
    if down == 1:
        prefix = _degree_prefix(generations=up - 2)
        return _gendered(sex=sex, male=f"{prefix}onkel".capitalize(), female=f"{prefix}tante".capitalize())
    if up == 1:
        prefix = _degree_prefix(generations=down - 2)
        return _gendered(sex=sex, male=f"{prefix}neffe".capitalize(), female=f"{prefix}nichte".capitalize())
    if up == down:
        cousin = _gendered(sex=sex, male="Cousin", female="Cousine")
        degree = up - 1
        return cousin if degree == 1 else f"{cousin} {degree}. Grades"
    return None


def _partner_name(*, sex: str | None, married: bool) -> str:
    if married:
        return _gendered(sex=sex, male="Ehemann", female="Ehefrau", neutral="Ehepartner")
    return _gendered(sex=sex, male="Partner", female="Partnerin")


def _in_law_name(*, family: FamilyGraph, home_id: int, person_id: int) -> str | None:
    """
    The nearest relationship by marriage there is a word for: the person is the partner of a blood relative of the
    home person, or a blood relative of one of the home person's partners.
    """
    sex = family.sex.get(person_id)
    candidates = []
    for relative_id in family.partners.get(person_id, ()):
        distance = _blood_distance(family=family, from_id=home_id, to_id=relative_id)
        if distance:
            candidates.append((sum(distance), _partner_of_relative_name(distance=distance, sex=sex)))
    for partner_id in family.partners.get(home_id, ()):
        distance = _blood_distance(family=family, from_id=partner_id, to_id=person_id)
        if distance:
            candidates.append((sum(distance), _relative_of_partner_name(distance=distance, sex=sex)))
    named = sorted(candidate for candidate in candidates if candidate[1])
    return named[0][1] if named else None


def _partner_of_relative_name(*, distance: tuple[int, int], sex: str | None) -> str | None:
    """
    The partner of the home person's child, parent or sibling, or of an uncle, aunt, nephew or niece, who share
    the blood relative's word.
    """
    match distance:
        case (0, 1):
            return _gendered(sex=sex, male="Schwiegersohn", female="Schwiegertochter", neutral="Schwiegerkind")
        case (1, 0):
            return _gendered(sex=sex, male="Stiefvater", female="Stiefmutter", neutral="Stiefelternteil")
    return _collateral_name(distance=distance, sex=sex)


def _relative_of_partner_name(*, distance: tuple[int, int], sex: str | None) -> str | None:
    """
    The parent, child, sibling, uncle, aunt, nephew or niece of the home person's partner.
    """
    match distance:
        case (1, 0):
            return _gendered(sex=sex, male="Schwiegervater", female="Schwiegermutter", neutral="Schwiegerelternteil")
        case (0, 1):
            return _gendered(sex=sex, male="Stiefsohn", female="Stieftochter", neutral="Stiefkind")
    return _collateral_name(distance=distance, sex=sex)


def _collateral_name(*, distance: tuple[int, int], sex: str | None) -> str | None:
    """
    By marriage, a sibling is a Schwager, and uncles, aunts, nephews and nieces keep their blood word.
    """
    up, down = distance
    if up == 1 and down == 1:
        return _gendered(sex=sex, male="Schwager", female="Schwägerin")
    if (up == 1 and down > 1) or (down == 1 and up > 1):
        return _blood_name(distance=distance, sex=sex)
    return None


def _connected(*, family: FamilyGraph, from_id: int, to_id: int) -> bool:
    seen: set[Node] = {from_id}
    frontier: list[Node] = [from_id]
    while frontier:
        node = frontier.pop()
        if node == to_id:
            return True
        unseen = family.neighbours.get(node, frozenset()) - seen
        seen |= unseen
        frontier.extend(unseen)
    return False
