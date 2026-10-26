"""
HTML that an export writes where GEDCOM expects text, turned back into text (#102). Pure functions: no database, no
Django.

MyHeritage writes the TEXT of a source as HTML. Stored as it comes, a person reads the tags themselves, and the
sections stick together without a line break.
"""

import html
import re

TAG = re.compile(r"</?([A-Za-z][A-Za-z0-9]*)[^<>]*>")
# Tags that sit inside a line and drop without a trace. Every other tag - a paragraph, a line break, an item, and one
# this list does not know - ends the line, so two sections never run into one another.
INLINE_TAGS = frozenset(
    {
        "a",
        "abbr",
        "b",
        "cite",
        "code",
        "em",
        "font",
        "i",
        "mark",
        "q",
        "s",
        "small",
        "span",
        "strike",
        "strong",
        "sub",
        "sup",
        "u",
    }
)
SPACES = re.compile(r"[ \t\xa0]+")


def plain_text(*, text: str) -> str:
    """
    "<p>Kirchenbuch</p><p>Band&nbsp;3</p>" as "Kirchenbuch\nBand 3": tags gone, entities resolved, one line per block.
    A text without a tag is returned as it is - an "&" in it is an ampersand, not the start of an entity.
    """
    if not TAG.search(text):
        return text
    broken = TAG.sub(lambda tag: "" if tag.group(1).lower() in INLINE_TAGS else "\n", text)
    lines = (SPACES.sub(" ", line).strip() for line in html.unescape(broken).splitlines())
    return "\n".join(line for line in lines if line)
