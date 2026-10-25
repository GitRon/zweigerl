"""
The import of a GEDCOM file into an empty tree (#22), with its sources, citations and notes (#23). What maps to
what is docs/patterns/gedcom.md, "The import"; reading the file and mapping it is "domain.gedcom" and
"domain.gedcom_import".
"""

from dataclasses import dataclass
from typing import BinaryIO

from django.core.exceptions import ValidationError
from django.db import transaction
from ged4py.parser import IntegrityError, ParserError

from apps.family_tree.domain.gedcom import read
from apps.family_tree.domain.gedcom_import import (
    ImportedFact,
    ImportedFamily,
    ImportedPerson,
    ImportedSource,
    read_tree,
)
from apps.family_tree.models import (
    Citation,
    Fact,
    GedcomImport,
    Note,
    ParentChild,
    Partnership,
    Person,
    SiblingPair,
    Source,
    TreeSettings,
)


class ImportRefusedError(Exception):
    """
    The import did not happen, with a German message saying why. Nothing was written.
    """


@dataclass(frozen=True, kw_only=True)
class ImportResult:
    gedcom_import: GedcomImport
    people: int
    families: int
    facts: int
    sources: int
    citations: int
    notes: int


@transaction.atomic
def import_gedcom(*, file: BinaryIO, name: str) -> ImportResult:
    """
    Reads a GEDCOM file into the tree under the name of the import - "PAF Ronny" - which every row it writes
    keeps as its Herkunft. Only into an empty tree: merging with people already there is #35. The first person
    of the file becomes the home person, as the export (#26) writes the home person first. Every row goes
    through "save()", so the rules of the models hold for an import as for a form.

    Raises "ImportRefusedError" for a tree that is not empty, a file that is not GEDCOM and a row the models
    refuse - all in one transaction, so a refused import leaves nothing behind.
    """
    if Person.objects.exists():
        raise ImportRefusedError(
            "Importiert wird nur in einen leeren Stammbaum. Hier stehen schon Personen - "
            "zusammenführen kann Zweigerl noch nicht."
        )
    try:
        tree = read_tree(records=read(file=file))
    except (ParserError, IntegrityError, UnicodeDecodeError, OSError) as error:
        raise ImportRefusedError(f"Das ist keine GEDCOM-Datei, die Zweigerl lesen kann: {error}") from error

    try:
        origin = GedcomImport(name=name.strip())
        origin.save()
    except ValidationError as error:
        raise ImportRefusedError(" ".join(error.messages)) from error
    sources = {source.xref: _source(source=source, origin=origin) for source in tree.sources}
    people = {person.xref: _person(person=person, origin=origin, sources=sources) for person in tree.people}
    for family in tree.families:
        _family(family=family, people=people, origin=origin, sources=sources)
    if tree.people:
        TreeSettings.objects.update_or_create(
            pk=TreeSettings.ONLY_ROW, defaults={"home_person": people[tree.people[0].xref]}
        )

    return ImportResult(
        gedcom_import=origin,
        people=len(tree.people),
        families=len(tree.families),
        # The facts written, not the ones read: a family of one parent has no row for its wedding.
        facts=Fact.objects.filter(gedcom_import=origin).count(),
        sources=len(sources),
        # Those written: a citation of a source the file does not have is left out.
        citations=Citation.objects.filter(gedcom_import=origin).count(),
        notes=Note.objects.filter(gedcom_import=origin).count(),
    )


def _source(*, source: ImportedSource, origin: GedcomImport) -> Source:
    row = Source(title=source.title, description=source.description, gedcom_raw=source.raw, gedcom_import=origin)
    _save(row=row, xref=source.xref)
    return row


def _person(*, person: ImportedPerson, origin: GedcomImport, sources: dict[str, Source]) -> Person:
    row = Person(
        given_names=person.given_names,
        surname=person.surname,
        call_name=person.call_name,
        sex=person.sex,
        living_status=Person.LivingStatus.DECEASED if person.deceased else Person.LivingStatus.UNKNOWN,
        gedcom_raw=person.raw,
        gedcom_import=origin,
    )
    _save(row=row, xref=person.xref)
    for fact in person.facts:
        _fact(fact=fact, origin=origin, sources=sources, xref=person.xref, person=row)
    for note in person.notes:
        _save(row=Note(person=row, text=note.text, gedcom_raw=note.raw, gedcom_import=origin), xref=person.xref)
    row.filed_sources.set(sources[xref] for xref in person.sources if xref in sources)
    return row


def _family(
    *, family: ImportedFamily, people: dict[str, Person], origin: GedcomImport, sources: dict[str, Source]
) -> None:
    """
    A couple becomes a Partnership with its children; a parent on their own is linked to the children alone; a
    family without parents makes its children siblings. What the family itself carries - its facts, what it keeps
    raw - has a row to live on only as a Partnership, its raw as a SiblingPair too. What a child's link carries
    raw goes on the link of the first parent alone, since the export writes the links of a child into one FAMC.
    """
    parents = [people[xref] for xref in family.parents if xref in people]
    children = [(child, people[child.xref]) for child in family.children if child.xref in people]
    partnership = None
    if len(parents) == 2:
        partnership = Partnership(
            person_a=parents[0],
            person_b=parents[1],
            kind=Partnership.Kind.MARRIAGE if family.married else Partnership.Kind.UNKNOWN,
            gedcom_raw=family.raw,
            gedcom_import=origin,
        )
        _save(row=partnership, xref=family.xref)
        for fact in family.facts:
            _fact(fact=fact, origin=origin, sources=sources, xref=family.xref, partnership=partnership)
    for child, row in children:
        for index, parent in enumerate(parents):
            link = ParentChild(
                parent=parent,
                child=row,
                partnership=partnership,
                pedigree=child.pedigree,
                gedcom_raw=child.raw if index == 0 else [],
                gedcom_import=origin,
            )
            _save(row=link, xref=family.xref)
    if not parents and len(children) > 1:
        (_, first), *others = children
        for index, (_, other) in enumerate(others):
            pair = SiblingPair(
                person_a=first, person_b=other, gedcom_raw=family.raw if index == 0 else [], gedcom_import=origin
            )
            _save(row=pair, xref=family.xref)


def _fact(
    *,
    fact: ImportedFact,
    origin: GedcomImport,
    sources: dict[str, Source],
    xref: str,
    person: Person | None = None,
    partnership: Partnership | None = None,
) -> None:
    """
    One fact with its citations. It stays "belegt" either way: with a citation it is documented for real, without
    one it shows as "unbelegt" - see docs/patterns/evidence.md. A citation of a source the file does not have is
    left out, as a pointer meaning nothing.
    """
    date = fact.date
    row = Fact(
        person=person,
        partnership=partnership,
        kind=fact.kind,
        value=fact.value,
        date_kind=date.kind if date else "",
        date_1=date.date_1 if date else None,
        date_2=date.date_2 if date else None,
        precision=date.precision if date else "",
        gedcom_raw=fact.raw,
        gedcom_import=origin,
    )
    _save(row=row, xref=xref)
    for citation in fact.citations:
        if citation.source in sources:
            cited = Citation(
                fact=row,
                source=sources[citation.source],
                page=citation.page,
                gedcom_raw=citation.raw,
                gedcom_import=origin,
            )
            _save(row=cited, xref=xref)


def _save(
    *, row: Person | Partnership | ParentChild | SiblingPair | Fact | Source | Citation | Note, xref: str
) -> None:
    """
    Saves one row, naming the record of the file it comes from when the models refuse it.
    """
    try:
        row.save()
    except ValidationError as error:
        raise ImportRefusedError(f"{xref} in der Datei: {' '.join(error.messages)}") from error
