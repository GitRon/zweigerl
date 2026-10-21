"""
The import of a GEDCOM file into an empty tree (#22). What maps to what is docs/patterns/gedcom.md, "The import";
reading the file and mapping it is "domain.gedcom" and "domain.gedcom_import".
"""

from dataclasses import dataclass
from typing import BinaryIO

from django.core.exceptions import ValidationError
from django.db import transaction
from ged4py.parser import IntegrityError, ParserError

from apps.family_tree.domain.gedcom import read
from apps.family_tree.domain.gedcom_import import ImportedFact, ImportedFamily, ImportedPerson, read_tree
from apps.family_tree.models import (
    Fact,
    GedcomImport,
    ParentChild,
    Partnership,
    Person,
    SiblingPair,
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
    people = {person.xref: _person(person=person, origin=origin) for person in tree.people}
    for family in tree.families:
        _family(family=family, people=people, origin=origin)
    if tree.people:
        TreeSettings.objects.update_or_create(
            pk=TreeSettings.ONLY_ROW, defaults={"home_person": people[tree.people[0].xref]}
        )

    return ImportResult(
        gedcom_import=origin,
        people=len(tree.people),
        families=len(tree.families),
        facts=sum(len(person.facts) for person in tree.people) + sum(len(family.facts) for family in tree.families),
    )


def _person(*, person: ImportedPerson, origin: GedcomImport) -> Person:
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
        _save(row=_fact(fact=fact, origin=origin, person=row), xref=person.xref)
    return row


def _family(*, family: ImportedFamily, people: dict[str, Person], origin: GedcomImport) -> None:
    """
    A couple becomes a Partnership with its children; a parent on their own is linked to the children alone; a
    family without parents makes its children siblings. What the family itself carries raw has a row to live on
    only as a Partnership or a SiblingPair.
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
            _save(row=_fact(fact=fact, origin=origin, partnership=partnership), xref=family.xref)
    for child, row in children:
        for parent in parents:
            link = ParentChild(
                parent=parent,
                child=row,
                partnership=partnership,
                pedigree=child.pedigree,
                gedcom_raw=child.raw,
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
    *, fact: ImportedFact, origin: GedcomImport, person: Person | None = None, partnership: Partnership | None = None
) -> Fact:
    date = fact.date
    return Fact(
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


def _save(*, row: Person | Partnership | ParentChild | SiblingPair | Fact, xref: str) -> None:
    """
    Saves one row, naming the record of the file it comes from when the models refuse it.
    """
    try:
        row.save()
    except ValidationError as error:
        raise ImportRefusedError(f"{xref} in der Datei: {' '.join(error.messages)}") from error
