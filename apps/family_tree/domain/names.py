"""
How a person's name is shown, sorted and searched. Pure functions: no database, no Django.

A person is shown by the name they went by - the Rufname, else the first given name - with the family name,
as in the mockup (#10, #30).
"""

NO_NAME = "Ohne Namen"

# DIN 5007-1, the order of a German dictionary and a phone book: an umlaut sorts as its base letter, "ß" as
# "ss" - which "casefold" already does. SQLite's ORDER BY compares code points and would put "Öhler" after
# "Zach".
SORT_LETTERS = str.maketrans({"ä": "a", "ö": "o", "ü": "u"})


def display_name(*, given_names: str, surname: str, call_name: str) -> str:
    """
    "Gerti Huber" for Gertrud with the Rufname Gerti, "Johann Huber" for Johann Georg, "Ohne Namen" for
    somebody nobody has named yet.
    """
    first = call_name.strip() or next(iter(given_names.split()), "")
    return " ".join(part for part in (first, surname.strip()) if part) or NO_NAME


def initials(*, given_names: str, surname: str) -> str:
    """
    The first letters of the first given name and the family name, for the picture frame. Empty when the
    person has no name, so the frame shows its placeholder instead.
    """
    first = next(iter(given_names.split()), "")
    return "".join(part[0] for part in (first, surname.strip()) if part).upper()


def sort_key(*, given_names: str, surname: str) -> tuple[bool, str, str]:
    """
    Sorts by family name, then given names, in German dictionary order and regardless of case. People
    without a family name come last rather than first, where they would push the family off the top.
    """
    return (not surname.strip(), _folded(text=surname), _folded(text=given_names))


def matches(*, search: str, names: tuple[str, ...]) -> bool:
    """
    Whether every word of "search" occurs in one of "names", ignoring case and telling neither an umlaut from
    its base letter nor "ß" from "ss": "lena hub" finds Lena Huber, "gossl" finds Gößl. An empty search
    matches everybody.
    """
    folded_names = [_folded(text=name) for name in names]
    return all(any(word in name for name in folded_names) for word in _folded(text=search).split())


def _folded(*, text: str) -> str:
    return text.casefold().translate(SORT_LETTERS).strip()
