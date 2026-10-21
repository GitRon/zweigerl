"""
What a GEDCOM file says, in the shape Zweigerl stores it (#22) - see docs/patterns/gedcom.md, "The import".

Pure functions: no database, no Django. "domain.gedcom.read" turns the file into nodes; "read_tree" maps the INDI
and FAM records onto people, families and their facts, and keeps what Zweigerl does not understand as raw
structures beside the row it belongs to. Nothing is guessed: a date Zweigerl cannot read stays raw, and somebody
without a death record is not known to be alive.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from apps.family_tree.domain.dates import UncertainDate, from_gedcom
from apps.family_tree.domain.gedcom import Node, raw_list, to_raw

# The longest value a fact holds - "Fact.value". A longer one stays raw rather than failing the whole import.
FACT_VALUE_LENGTH = 300

# The events that carry a date, by the kind of fact they become. A birth is read on its own, since its place is a
# fact too.
DATE_EVENTS = {"CHR": "baptism", "BAPM": "baptism", "DEAT": "death", "BURI": "burial"}
VALUE_ATTRIBUTES = {"OCCU": "occupation"}
COUPLE_EVENTS = {"MARR": "marriage", "DIV": "divorce"}
# An event that says only that it happened. A death says it with the person's status, a wedding with the kind of
# the partnership, and the export writes either back - so neither is kept raw too.
SAID_BY_STATUS = ("DEAT", "MARR")
# The records of a person that mean they died.
DEATH_RECORDS = ("DEAT", "BURI")

SEXES = ("M", "F", "X", "U")
PEDIGREES = {"birth": "birth", "adopted": "adopted", "foster": "foster"}

NAME = re.compile(r"^(?P<given>[^/]*)(?:/(?P<surname>[^/]*)/?)?")


@dataclass(frozen=True, kw_only=True)
class ImportedFact:
    # A "Fact.Kind", and a value or a date - never both, since GEDCOM's own events are never "custom".
    kind: str
    value: str = ""
    date: UncertainDate | None = None
    raw: list[dict] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class ImportedPerson:
    xref: str
    given_names: str = ""
    surname: str = ""
    call_name: str = ""
    sex: str = "U"
    # A DEAT or BURI is there. Without one, the person is "unknown", never "living".
    deceased: bool = False
    facts: list[ImportedFact] = field(default_factory=list)
    raw: list[dict] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class ImportedChild:
    xref: str
    pedigree: str = "birth"
    # What the child's FAMC and the family's CHIL carry beside the pointer.
    raw: list[dict] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class ImportedFamily:
    xref: str
    # HUSB and WIFE, in the order the file names them: none, one or two.
    parents: tuple[str, ...]
    children: list[ImportedChild] = field(default_factory=list)
    # A MARR is there, with a date Zweigerl can read or not.
    married: bool = False
    facts: list[ImportedFact] = field(default_factory=list)
    raw: list[dict] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class ImportedTree:
    # In the order of the file: the first one becomes the home person.
    people: list[ImportedPerson]
    families: list[ImportedFamily]


@dataclass(kw_only=True)
class _Person:
    # A person while their record is being read, and what belongs to their families instead.
    xref: str
    given_names: str = ""
    surname: str = ""
    call_name: str = ""
    sex: str = "U"
    deceased: bool = False
    named: bool = False
    facts: list[ImportedFact] = field(default_factory=list)
    raw: list[dict] = field(default_factory=list)
    as_partner: list[str] = field(default_factory=list)
    # Each FAMC by the family's xref, with what it carries.
    as_child: dict[str, Node] = field(default_factory=dict)
    divorces: list[Node] = field(default_factory=list)


def read_tree(*, records: list[Node]) -> ImportedTree:
    """
    The people and families of a GEDCOM file. HEAD, SUBM and the other records are left out - SOUR and NOTE
    records come with #23. A DIV under a person goes to their family when they have exactly one, and stays
    raw on the person otherwise.
    """
    people = [_person(record=record) for record in records if record.tag == "INDI" and record.xref]
    divorces: dict[str, list[Node]] = {}
    for person in people:
        if len(person.as_partner) == 1:
            divorces.setdefault(person.as_partner[0], []).extend(person.divorces)
        else:
            person.raw.extend(raw_list(nodes=person.divorces))
    as_child = {(person.xref, family): famc for person in people for family, famc in person.as_child.items()}
    return ImportedTree(
        people=[_frozen(person=person) for person in people],
        families=[
            _family(record=record, divorces=divorces.get(record.xref, []), as_child=as_child)
            for record in records
            if record.tag == "FAM" and record.xref
        ],
    )


def _frozen(*, person: _Person) -> ImportedPerson:
    return ImportedPerson(
        xref=person.xref,
        given_names=person.given_names,
        surname=person.surname,
        call_name=person.call_name,
        sex=person.sex,
        deceased=person.deceased,
        facts=person.facts,
        raw=person.raw,
    )


def _person(*, record: Node) -> _Person:
    person = _Person(xref=record.xref)
    for node in record.children:
        if node.tag in DEATH_RECORDS:
            person.deceased = True
        _PERSON_TAGS.get(node.tag, _keep_raw)(person=person, node=node)
    return person


def _read_name(*, person: _Person, node: Node) -> None:
    """
    The first NAME: GIVN, SURN and NICK where the file has them, otherwise what "Given /Surname/" says. Its
    other parts - a title, a married name, an alias - stay raw as a NAME without a value, which the export
    merges into its own. A second NAME stays raw whole.
    """
    if person.named:
        person.raw.append(to_raw(node=node))
        return
    person.named = True
    parts = {child.tag: child.value for child in node.children}
    written = NAME.match(node.value)
    person.given_names = parts.get("GIVN", (written["given"] or "").strip())
    person.surname = parts.get("SURN", (written["surname"] or "").strip())
    person.call_name = parts.get("NICK", "")
    if rest := raw_list(nodes=[child for child in node.children if child.tag not in ("GIVN", "SURN", "NICK")]):
        person.raw.append({"tag": "NAME", "children": rest})


def _read_sex(*, person: _Person, node: Node) -> None:
    if node.value in SEXES:
        person.sex = node.value
    else:
        person.raw.append(to_raw(node=node))


def _read_birth(*, person: _Person, node: Node) -> None:
    """
    A BIRT is two facts, the date and the place - see docs/patterns/evidence.md. What else it carries goes along
    with the date, or with the place when there is no date Zweigerl can read; a BIRT without either stays raw.
    """
    date_node = _first(node=node, tag="DATE")
    date = _date(node=date_node)
    place_node = _first(node=node, tag="PLAC")
    if place_node is not None and not 0 < len(place_node.value) <= FACT_VALUE_LENGTH:
        place_node = None
    rest = [child for child in node.children if child is not place_node and (child is not date_node or date is None)]
    facts = []
    if date is not None:
        facts.append(ImportedFact(kind="birth", date=date, raw=raw_list(nodes=rest)))
        rest = []
    if place_node is not None:
        place_raw = raw_list(nodes=[*place_node.children, *rest])
        facts.append(ImportedFact(kind="birthplace", value=place_node.value, raw=place_raw))
    if facts:
        person.facts.extend(facts)
    else:
        person.raw.append(to_raw(node=node))


def _read_dated(*, person: _Person, node: Node) -> None:
    if fact := _dated(node=node, kind=DATE_EVENTS[node.tag]):
        person.facts.append(fact)
    elif not _said_by_status(node=node):
        person.raw.append(to_raw(node=node))


def _read_attribute(*, person: _Person, node: Node) -> None:
    """
    An attribute with its value on the line. A date or a place below it stays raw below the fact, since a
    value fact has neither.
    """
    if 0 < len(node.value) <= FACT_VALUE_LENGTH:
        person.facts.append(
            ImportedFact(kind=VALUE_ATTRIBUTES[node.tag], value=node.value, raw=raw_list(nodes=node.children))
        )
    else:
        person.raw.append(to_raw(node=node))


def _read_partner(*, person: _Person, node: Node) -> None:
    if node.pointer:
        person.as_partner.append(node.pointer)
    else:
        person.raw.append(to_raw(node=node))


def _read_child(*, person: _Person, node: Node) -> None:
    if node.pointer:
        person.as_child[node.pointer] = node
    else:
        person.raw.append(to_raw(node=node))


def _read_divorce(*, person: _Person, node: Node) -> None:
    person.divorces.append(node)


def _keep_raw(*, person: _Person, node: Node) -> None:
    # "to_raw" leaves out a pointer below the node, "raw_list" one at the top too - a SOUR citing a record.
    person.raw.extend(raw_list(nodes=[node]))


_PERSON_TAGS: dict[str, Callable[..., None]] = {
    "NAME": _read_name,
    "SEX": _read_sex,
    "BIRT": _read_birth,
    **dict.fromkeys(DATE_EVENTS, _read_dated),
    **dict.fromkeys(VALUE_ATTRIBUTES, _read_attribute),
    "FAMS": _read_partner,
    "FAMC": _read_child,
    "DIV": _read_divorce,
}


def _family(*, record: Node, divorces: list[Node], as_child: dict[tuple[str, str], Node]) -> ImportedFamily:
    """
    One FAM: its parents, its children with how each belongs to it, the wedding and the divorce. Everything else
    on it stays raw.
    """
    parents = tuple(node.pointer for node in record.children if node.tag in ("HUSB", "WIFE") and node.pointer)
    children = [
        _child(chil=node, famc=as_child.get((node.pointer, record.xref)))
        for node in record.children
        if node.tag == "CHIL" and node.pointer
    ]
    facts, raw = _couple_facts(nodes=[*record.children, *divorces])
    married = any(node.tag == "MARR" for node in record.children)
    return ImportedFamily(xref=record.xref, parents=parents, children=children, married=married, facts=facts, raw=raw)


def _couple_facts(*, nodes: list[Node]) -> tuple[list[ImportedFact], list[dict]]:
    """
    The wedding and the divorce of a family as facts, and what else it carries as raw structures - its members
    are not among them, unless a line names one without a pointer.
    """
    facts, raw = [], []
    for node in nodes:
        if node.tag in COUPLE_EVENTS:
            if fact := _dated(node=node, kind=COUPLE_EVENTS[node.tag]):
                facts.append(fact)
            elif not _said_by_status(node=node):
                raw.append(to_raw(node=node))
        elif node.tag not in ("HUSB", "WIFE", "CHIL") or not node.pointer:
            raw.extend(raw_list(nodes=[node]))
    return facts, raw


def _child(*, chil: Node, famc: Node | None) -> ImportedChild:
    """
    A child of a family. Its PEDI is on the child's FAMC; one Zweigerl has no word for stays raw there, and the
    child counts as "unknown".
    """
    below = list(famc.children) if famc else []
    pedi = _first(node=famc, tag="PEDI") if famc else None
    pedigree = "birth"
    if pedi is not None:
        pedigree = PEDIGREES.get(pedi.value.lower(), "unknown")
        if pedigree != "unknown":
            below.remove(pedi)
    return ImportedChild(xref=chil.pointer, pedigree=pedigree, raw=raw_list(nodes=[*below, *chil.children]))


def _dated(*, node: Node, kind: str) -> ImportedFact | None:
    """
    An event with a date Zweigerl can read, as a fact carrying what else is below it - a place, a cause - raw.
    None without one: the caller keeps the whole event raw.
    """
    date_node = _first(node=node, tag="DATE")
    date = _date(node=date_node)
    if date is None:
        return None
    return ImportedFact(
        kind=kind, date=date, raw=raw_list(nodes=[child for child in node.children if child is not date_node])
    )


def _date(*, node: Node | None) -> UncertainDate | None:
    if node is None:
        return None
    try:
        return from_gedcom(text=node.value)
    except ValueError:
        return None


def _said_by_status(*, node: Node) -> bool:
    return node.tag in SAID_BY_STATUS and not node.children and node.value in ("", "Y")


def _first(*, node: Node, tag: str) -> Node | None:
    return next((child for child in node.children if child.tag == tag), None)
