"""
GEDCOM 5.5.1 as lines - see docs/patterns/gedcom.md.

Pure functions: no database, no Django. The reader builds the records of an export (#26) as "Node"s; this module
writes them out as text, and turns what an import kept raw in "gedcom_raw" back into nodes. An import (#22)
goes the other way: "read" turns a file into nodes, "to_raw" a node into what "gedcom_raw" keeps.
"""

import io
import re
from dataclasses import dataclass, field
from typing import BinaryIO

from ged4py.parser import GedcomReader, guess_codec

# GEDCOM 5.5.1 allows 255 characters on a line, level, tag and terminator included. A value is cut into pieces
# of at most this many characters, which leaves room for any level and tag in front of it.
MAX_VALUE_LENGTH = 200

# A line pointing at a record: "@I1@". "@@" in a value is an escaped "@", and "@#DJULIAN@" starts a date in
# another calendar - neither is a pointer.
POINTER = re.compile(r"^@[^@#][^@]*@$")


@dataclass(frozen=True, kw_only=True)
class Node:
    """
    One line with what hangs below it. A record carries its "xref" ("@I1@"); a line pointing at a record carries
    a "pointer" instead of a "value", and only a value is escaped.
    """

    tag: str
    value: str = ""
    pointer: str = ""
    xref: str = ""
    children: tuple[Node, ...] = field(default_factory=tuple)


def from_raw(*, records: list[dict]) -> tuple[Node, ...]:
    """
    The nodes of what an import kept in "gedcom_raw": a list of structures {"tag", "value", "children"}, the
    last two optional - see docs/patterns/family.md, "Raw GEDCOM".
    """
    return tuple(
        Node(
            tag=record["tag"],
            value=record.get("value", ""),
            children=from_raw(records=record.get("children", [])),
        )
        for record in records
    )


def to_raw(*, node: Node) -> dict:
    """
    What "gedcom_raw" keeps of a node: its tag, its value and its children, the last two only when there are
    any. A child pointing at a record is left out, since its xref means nothing outside the file it came from.
    """
    raw: dict = {"tag": node.tag}
    if node.value:
        raw["value"] = node.value
    if children := raw_list(nodes=node.children):
        raw["children"] = children
    return raw


def raw_list(*, nodes: tuple[Node, ...] | list[Node]) -> list[dict]:
    """
    The raw structures of several nodes, those pointing at a record left out.
    """
    return [to_raw(node=node) for node in nodes if not node.pointer]


@dataclass(kw_only=True)
class _Open:
    # A node still being read: CONC and CONT lines may still add to its value, and children may follow.
    tag: str
    xref: str
    value: bytes
    children: list[_Open] = field(default_factory=list)


def read(*, file: BinaryIO) -> list[Node]:
    """
    The records of a GEDCOM file, each with everything below it. ged4py finds the character set - a BOM, the
    "CHAR" of the header, ANSEL - and reads the lines; a CONC continues a value without a space, a CONT on a new
    line. Both are joined as bytes before decoding, since some programs cut a line in the middle of a character.
    Raises ged4py's "ParserError" or "IntegrityError" for a file that is not GEDCOM, and "UnicodeDecodeError"
    for one that is not in the character set it names.
    """
    # ged4py closes the file it reads once it is done with it, so it gets a copy rather than the caller's.
    file.seek(0)
    data = io.BytesIO(file.read())
    codec, bom_size = guess_codec(data)
    data.seek(0)
    records: list[_Open] = []
    stack: list[_Open] = []
    for line in GedcomReader(data, encoding=codec).GedcomLines(bom_size):
        value = line.value or b""
        # ged4py has already refused a CONC or CONT that is not one level below the line it continues.
        if line.tag in ("CONC", "CONT"):
            stack[line.level - 1].value += (b"\n" if line.tag == "CONT" else b"") + value
            continue
        node = _Open(tag=line.tag, xref=line.xref_id or "", value=value)
        del stack[line.level :]
        (stack[-1].children if stack else records).append(node)
        stack.append(node)
    return [_closed(node=node, codec=codec) for node in records]


def _closed(*, node: _Open, codec: str) -> Node:
    text = node.value.decode(codec)
    children = tuple(_closed(node=child, codec=codec) for child in node.children)
    if POINTER.match(text):
        return Node(tag=node.tag, xref=node.xref, pointer=text, children=children)
    return Node(tag=node.tag, xref=node.xref, value=text.replace("@@", "@"), children=children)


def write(*, records: list[Node]) -> str:
    """
    The records as GEDCOM text, each at level 0: a line break in a value continues on a CONT line, a value
    longer than a line on CONC lines, and an "@" in a value is doubled, as GEDCOM 5.5.1 asks.
    """
    lines = []
    for record in records:
        lines.extend(_lines(node=record, level=0))
    return "\n".join(lines) + "\n"


def _lines(*, node: Node, level: int) -> list[str]:
    head = f"{level} {node.xref} {node.tag}" if node.xref else f"{level} {node.tag}"
    if node.pointer:
        lines = [f"{head} {node.pointer}"]
    else:
        # A text from a form breaks its lines with "\r\n"
        first, *more = node.value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        lines = _with_value(head=head, text=first, level=level)
        for text in more:
            lines.extend(_with_value(head=f"{level + 1} CONT", text=text, level=level))
    for child in node.children:
        lines.extend(_lines(node=child, level=level + 1))
    return lines


def _with_value(*, head: str, text: str, level: int) -> list[str]:
    """
    One line of a value, and the CONC lines its rest needs - one level below the line they continue.
    """
    pieces = _pieces(text=text)
    lines = [f"{head} {_escape(text=pieces[0])}" if pieces[0] else head]
    lines.extend(f"{level + 1} CONC {_escape(text=piece)}" for piece in pieces[1:])
    return lines


def _pieces(*, text: str) -> list[str]:
    """
    The text cut into pieces short enough for a line, never at a space: a reader may drop a space at the end or
    the start of a line, and the words on both sides would then run together.
    """
    pieces = []
    while len(text) > MAX_VALUE_LENGTH:
        cut = MAX_VALUE_LENGTH
        while cut > 1 and (text[cut - 1] == " " or text[cut] == " "):
            cut -= 1
        if cut == 1:
            cut = MAX_VALUE_LENGTH
        pieces.append(text[:cut])
        text = text[cut:]
    pieces.append(text)
    return pieces


def _escape(*, text: str) -> str:
    return text.replace("@", "@@")
