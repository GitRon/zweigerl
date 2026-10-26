"""
HTML that an export writes where GEDCOM expects text, turned back into text (#102). Pure functions: no database, no
Django.

MyHeritage writes the TEXT of a source as HTML. Stored as it comes, a person reads the tags themselves, and the
sections stick together without a line break.
"""

import re
from html.parser import HTMLParser

TAG = re.compile(r"</?[A-Za-z][^<>]*>")
# Tags that sit inside a line and drop without a trace. Every other tag - a paragraph, a line break, an item, and one
# this list does not know - ends the line, so two sections never run into one another.
INLINE_TAGS = frozenset({
    "a", "abbr", "b", "cite", "code", "em", "font", "i", "mark", "q", "s", "small", "span", "strike", "strong",
    "sub", "sup", "u",
})
SPACES = re.compile(r"[ \t\xa0]+")


def plain_text(*, text: str) -> str:
    """
    "<p>Kirchenbuch</p><p>Band&nbsp;3</p>" as "Kirchenbuch\nBand 3": tags gone, entities resolved, one line per block.
    A text without a tag is returned as it is - an "&" in it is an ampersand, not the start of an entity.
    """
    if not TAG.search(text):
        return text
    parser = _TextParser()
    parser.feed(text)
    parser.close()
    lines = (SPACES.sub(" ", line).strip() for line in "".join(parser.parts).splitlines())
    return "\n".join(line for line in lines if line)


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._break(tag=tag)

    def handle_endtag(self, tag: str) -> None:
        self._break(tag=tag)

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def _break(self, *, tag: str) -> None:
        if tag not in INLINE_TAGS:
            self.parts.append("\n")
