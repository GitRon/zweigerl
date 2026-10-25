"""
What a GEDCOM file would bring before it is imported (#25) - see docs/patterns/gedcom.md, "The import".

Pure functions: no database, no Django. The file is read the way the import reads it, "domain.gedcom.read" and
"domain.gedcom_import.read_tree", and nothing is written: the preview counts what comes, names what the program
that wrote the file brings along, and warns about what looks wrong.
"""

import datetime
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import BinaryIO

from ged4py.parser import IntegrityError, ParserError

from apps.family_tree.domain.dates import from_gedcom
from apps.family_tree.domain.gedcom import Node, read
from apps.family_tree.domain.gedcom_import import read_tree

URL = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
WINDOWS_PATH = re.compile(r"^[a-z]:[\\/]|\\", re.IGNORECASE)
# The lines that hold where somebody lives or how to reach them - mostly of the living (#84).
CONTACT_TAGS = ("ADDR", "EMAIL")
# A CHAN says when the record was last changed in the program, not when something happened.
NOT_AN_EVENT = "CHAN"


class UnreadableGedcomError(ValueError):
    """
    The file is no GEDCOM Zweigerl can read, with a German message saying why.
    """


@dataclass(frozen=True, kw_only=True)
class Preview:
    # HEAD/SOUR - "PAF", "MyHeritage" - and HEAD/CHAR, each empty when the file does not say.
    program: str
    charset: str
    people: int
    families: int
    sources: int
    # The FILE of every OBJE, by what it points at.
    photos_windows: int
    photos_url: int
    photos_other: int
    # The tags of the program's own, starting with "_", each once.
    own_tags: tuple[str, ...]
    # Warnings.
    unnamed: int
    future_dates: int
    with_contact: int
    unreadable_dates: int

    @property
    def photos(self) -> int:
        return self.photos_windows + self.photos_url + self.photos_other

    @property
    def warnings(self) -> int:
        return self.unnamed + self.future_dates + self.with_contact + self.unreadable_dates


def preview_file(*, file: BinaryIO, today: datetime.date) -> Preview:
    """
    What the file would bring, without writing anything. Raises "UnreadableGedcomError" for a file that is not
    GEDCOM - the same files the import refuses as none.
    """
    try:
        records = read(file=file)
    except (ParserError, IntegrityError, UnicodeDecodeError, OSError) as error:
        raise UnreadableGedcomError(f"Das ist keine GEDCOM-Datei, die Zweigerl lesen kann: {error}") from error
    return preview(records=records, today=today)


def preview(*, records: list[Node], today: datetime.date) -> Preview:
    tree = read_tree(records=records)
    head = next((record for record in records if record.tag == "HEAD"), Node(tag="HEAD"))
    # The FILE of the HEAD names the file itself; a photo's FILE is below an OBJE.
    files = [
        _file_kind(path=child.value)
        for node in _below(nodes=records)
        if node.tag == "OBJE"
        for child in node.children
        if child.tag == "FILE"
    ]
    dates = [_read_date(text=node.value) for node in _event_dates(records=records)]
    return Preview(
        program=_value(node=head, tag="SOUR"),
        charset=_value(node=head, tag="CHAR"),
        people=len(tree.people),
        families=len(tree.families),
        sources=sum(1 for record in records if record.tag == "SOUR" and record.xref),
        photos_windows=files.count("windows"),
        photos_url=files.count("url"),
        photos_other=files.count("other"),
        own_tags=tuple(sorted({node.tag for node in _below(nodes=records) if node.tag.startswith("_")})),
        unnamed=sum(1 for person in tree.people if not person.given_names and not person.surname),
        future_dates=sum(1 for date in dates if date is not None and date > today),
        with_contact=sum(
            1
            for record in records
            if record.tag == "INDI" and any(node.tag in CONTACT_TAGS for node in _below(nodes=record.children))
        ),
        unreadable_dates=sum(1 for date in dates if date is None),
    )


def _below(*, nodes: tuple[Node, ...] | list[Node]) -> Iterator[Node]:
    for node in nodes:
        yield node
        yield from _below(nodes=node.children)


def _file_kind(*, path: str) -> str:
    if URL.match(path):
        return "url"
    if WINDOWS_PATH.search(path):
        return "windows"
    return "other"


def _event_dates(*, records: list[Node]) -> Iterator[Node]:
    """
    Every DATE of a person or a family, apart from the one saying when the program last changed the record.
    """
    for record in records:
        if record.tag in ("INDI", "FAM"):
            yield from (node for node in _below_events(nodes=record.children) if node.tag == "DATE")


def _below_events(*, nodes: tuple[Node, ...]) -> Iterator[Node]:
    for node in nodes:
        if node.tag != NOT_AN_EVENT:
            yield node
            yield from _below_events(nodes=node.children)


def _read_date(*, text: str) -> datetime.date | None:
    try:
        return from_gedcom(text=text).date_1
    except ValueError:
        return None


def _value(*, node: Node, tag: str) -> str:
    return next((child.value for child in node.children if child.tag == tag), "")
