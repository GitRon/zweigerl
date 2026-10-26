"""
What a GEDCOM file says, in the shape Zweigerl stores it (#22) - see docs/patterns/gedcom.md, "The import".

Pure functions: no database, no Django. "domain.gedcom.read" turns the file into nodes; "read_tree" maps the INDI,
FAM and SOUR records onto people, families, sources and their facts, citations and notes (#23), and keeps what
Zweigerl does not understand as raw structures beside the row it belongs to. Nothing is guessed: a date Zweigerl
cannot read stays raw, and somebody without a death record is not known to be alive.
"""

import datetime
import re
from collections.abc import Callable
from dataclasses import dataclass, field, replace

from apps.family_tree.domain.dates import DateKind, Precision, UncertainDate, from_gedcom
from apps.family_tree.domain.gedcom import Node, raw_list, to_raw
from apps.family_tree.domain.html_text import plain_text

# The longest value a fact holds - "Fact.value". A longer one stays raw rather than failing the whole import.
FACT_VALUE_LENGTH = 300
# The longest title of a source and page of a citation - "Source.title", "Citation.page" - the same way.
SOURCE_TITLE_LENGTH = 300
CITATION_PAGE_LENGTH = 300

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
# A day the German way, as MyHeritage writes some of them: "07.03.1962".
DOTTED_DAY = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{3,4})$")

# How sure a citation is, GEDCOM's QUAY from 0 to 3, as the reliability of the fact it cites - see
# docs/patterns/evidence.md. Direct and secondary evidence document it, questionable evidence makes it probable,
# unreliable evidence leaves it handed down.
RELIABILITY_BY_QUAY = {"3": "documented", "2": "documented", "1": "probable", "0": "handed_down"}
# The most reliable first: a fact cited several times takes the best of its citations.
RELIABILITIES = ("documented", "probable", "handed_down")


@dataclass(frozen=True, kw_only=True)
class ImportedCitation:
    # The xref of the SOUR record the fact cites, as the file names it.
    source: str
    page: str = ""
    # The QUAY, "0" to "3", which stays raw as well; empty without one.
    quality: str = ""
    raw: list[dict] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class ImportedFact:
    # A "Fact.Kind", and a value or a date - never both, since GEDCOM's own events are never "custom".
    kind: str
    value: str = ""
    date: UncertainDate | None = None
    citations: list[ImportedCitation] = field(default_factory=list)
    raw: list[dict] = field(default_factory=list)

    @property
    def reliability(self) -> str:
        """
        A "Fact.Reliability": what the best QUAY among its citations says, "documented" when none has one.
        """
        said = [RELIABILITY_BY_QUAY[cited.quality] for cited in self.citations if cited.quality in RELIABILITY_BY_QUAY]
        return min(said, key=RELIABILITIES.index, default="documented")


@dataclass(frozen=True, kw_only=True)
class ImportedNote:
    text: str
    # What the NOTE carries below it, and the lines of the NOTE record it points at.
    raw: list[dict] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class ImportedSource:
    xref: str
    title: str
    description: str = ""
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
    notes: list[ImportedNote] = field(default_factory=list)
    # The xrefs of the SOUR records the person is filed with - a SOUR pointer directly under the INDI.
    sources: list[str] = field(default_factory=list)
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
    sources: list[ImportedSource] = field(default_factory=list)


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
    notes: list[ImportedNote] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    raw: list[dict] = field(default_factory=list)
    # The NOTE records of the file by their xref, for a NOTE pointing at one.
    note_records: dict[str, Node] = field(default_factory=dict)
    as_partner: list[str] = field(default_factory=list)
    # Each FAMC by the family's xref, with what it carries.
    as_child: dict[str, Node] = field(default_factory=dict)
    divorces: list[Node] = field(default_factory=list)


def read_tree(*, records: list[Node]) -> ImportedTree:
    """
    The people, families and sources of a GEDCOM file. A NOTE record is read where a person's NOTE points at it;
    HEAD, SUBM and the other records are left out. A DIV under a person goes to their family when they have
    exactly one, and stays raw on the person otherwise.
    """
    note_records = {record.xref: record for record in records if record.tag == "NOTE" and record.xref}
    people = [
        _person(record=record, note_records=note_records) for record in records if record.tag == "INDI" and record.xref
    ]
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
        sources=[_source(record=record) for record in records if record.tag == "SOUR" and record.xref],
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
        notes=person.notes,
        sources=person.sources,
        raw=person.raw,
    )


def _person(*, record: Node, note_records: dict[str, Node]) -> _Person:
    person = _Person(xref=record.xref, note_records=note_records)
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
    A BIRT is two facts, the date and the place - see docs/patterns/evidence.md. What else it carries, its
    citations too, goes along with the date, or with the place when there is no date Zweigerl can read; a BIRT
    without either stays raw.
    """
    date_node = _first(node=node, tag="DATE")
    date = _date(node=date_node)
    place_node = _first(node=node, tag="PLAC")
    if place_node is not None and not 0 < len(place_node.value) <= FACT_VALUE_LENGTH:
        place_node = None
    rest = [child for child in node.children if child is not place_node and (child is not date_node or date is None)]
    facts = []
    if date is not None:
        citations, raw = _cited(nodes=rest)
        facts.append(ImportedFact(kind="birth", date=date, citations=citations, raw=raw))
        rest = []
    if place_node is not None:
        citations, raw = _cited(nodes=[*place_node.children, *rest])
        facts.append(ImportedFact(kind="birthplace", value=place_node.value, citations=citations, raw=raw))
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
        citations, raw = _cited(nodes=node.children)
        person.facts.append(
            ImportedFact(kind=VALUE_ATTRIBUTES[node.tag], value=node.value, citations=citations, raw=raw)
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


def _read_note(*, person: _Person, node: Node) -> None:
    """
    A NOTE becomes a note, with what it carries below it raw. One pointing at a NOTE record takes that record's
    text, and the record's own lines - its CHAN - raw. A NOTE without text stays raw; one pointing at a record
    the file does not have is left out, as a pointer meaning nothing.
    """
    if node.pointer:
        if (record := person.note_records.get(node.pointer)) is None:
            return
        text, raw = record.value, raw_list(nodes=[*record.children, *node.children])
    else:
        text, raw = node.value, raw_list(nodes=node.children)
    if text.strip():
        person.notes.append(ImportedNote(text=text, raw=raw))
    else:
        person.raw.append(to_raw(node=node))


def _read_source(*, person: _Person, node: Node) -> None:
    """
    A SOUR pointer directly under the INDI files the source with the person, as the export writes it. What it
    carries below - MyHeritage cites everything this way, with PAGE, QUAY and DATA - has no fact to be a citation
    of, so it stays raw on the person as a SOUR without the pointer. A SOUR with its text on the line cites no
    record and stays raw.
    """
    if node.pointer:
        person.sources.append(node.pointer)
        if node.children:
            person.raw.append(to_raw(node=node))
    else:
        person.raw.append(to_raw(node=node))


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
    "NOTE": _read_note,
    "SOUR": _read_source,
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
    citations, raw = _cited(nodes=[child for child in node.children if child is not date_node])
    return ImportedFact(kind=kind, date=date, citations=citations, raw=raw)


def _cited(*, nodes: tuple[Node, ...] | list[Node]) -> tuple[list[ImportedCitation], list[dict]]:
    """
    The citations among what hangs below a fact - each SOUR pointing at a record, with its PAGE - and the rest as
    raw structures. A fact cites a source once, so a second SOUR of the same record joins its page to the first,
    and the better of their QUAYs counts. A page too long for a citation stays raw below it. A SOUR with its text
    on the line cites no record and stays raw.
    """
    citations: dict[str, ImportedCitation] = {}
    for node in nodes:
        if node.tag != "SOUR" or not node.pointer:
            continue
        cited = citations.get(node.pointer, ImportedCitation(source=node.pointer))
        page_node = _first(node=node, tag="PAGE")
        page = "; ".join(part for part in (cited.page, page_node.value if page_node else "") if part)
        if len(page) > CITATION_PAGE_LENGTH:
            page_node, page = None, cited.page
        raw = raw_list(nodes=[child for child in node.children if child is not page_node])
        citations[node.pointer] = replace(
            cited, page=page, quality=_better_quality(known=cited.quality, sour=node), raw=[*cited.raw, *raw]
        )
    rest = [node for node in nodes if node.tag != "SOUR" or not node.pointer]
    return list(citations.values()), raw_list(nodes=rest)


def _better_quality(*, known: str, sour: Node) -> str:
    """
    The better of a citation's QUAY so far and the one below this SOUR - a higher one is better. A QUAY that is not
    0 to 3 counts as none.
    """
    quay = _first(node=sour, tag="QUAY")
    said = quay.value.strip() if quay else ""
    return max((value for value in (known, said) if value in RELIABILITY_BY_QUAY), default="")


def _source(*, record: Node) -> ImportedSource:
    """
    A SOUR record: its TITL is the title and its TEXT the description, as text even where the export wrote HTML
    (#102); what else it carries - an AUTH, a PUBL, an
    OBJE until #24 - stays raw. One without a title it can hold is named after its xref rather than refused, and
    its TITL stays raw.
    """
    title_node = _first(node=record, tag="TITL")
    if title_node is not None and not 0 < len(title_node.value.strip()) <= SOURCE_TITLE_LENGTH:
        title_node = None
    text_node = _first(node=record, tag="TEXT")
    rest = [child for child in record.children if child is not title_node and child is not text_node]
    return ImportedSource(
        xref=record.xref,
        title=title_node.value.strip() if title_node else f"Quelle {record.xref}",
        description=plain_text(text=text_node.value) if text_node else "",
        raw=raw_list(nodes=rest),
    )


def read_date(*, text: str) -> UncertainDate:
    """
    A date as an export writes it: GEDCOM 5.5.1, or a day the German way, "07.03.1962", which MyHeritage writes
    beside it. Raises ValueError for anything else - the import keeps that raw, the preview names it.
    """
    if match := DOTTED_DAY.match(text.strip()):
        day, month, year = (int(part) for part in match.groups())
        try:
            day_1 = datetime.date(year, month, day)
        except ValueError as error:
            raise ValueError(f"„{text}“ ist kein gültiges Datum.") from error
        return UncertainDate(kind=DateKind.EXACT, date_1=day_1, precision=Precision.DAY)
    return from_gedcom(text=text)


def _date(*, node: Node | None) -> UncertainDate | None:
    if node is None:
        return None
    try:
        return read_date(text=node.value)
    except ValueError:
        return None


def _said_by_status(*, node: Node) -> bool:
    return node.tag in SAID_BY_STATUS and not node.children and node.value in ("", "Y")


def _first(*, node: Node, tag: str) -> Node | None:
    return next((child for child in node.children if child.tag == tag), None)
