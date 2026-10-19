"""
GEDCOM 5.5.1 as lines - see docs/patterns/gedcom.md.

Pure functions: no database, no Django. The reader builds the records of an export (#26) as "Node"s; this module
writes them out as text, and turns what an import kept raw in "gedcom_raw" back into nodes.
"""

from dataclasses import dataclass, field

# GEDCOM 5.5.1 allows 255 characters on a line, level, tag and terminator included. A value is cut into pieces
# of at most this many characters, which leaves room for any level and tag in front of it.
MAX_VALUE_LENGTH = 200


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
