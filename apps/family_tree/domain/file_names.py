"""
What the files Zweigerl writes are called. Pure functions: no database, no Django.
"""

import re
import unicodedata

# Spelled out the way a German reads them, so "Gößl" becomes "goessl" rather than "gol". "casefold" already
# turns "ß" into "ss".
GERMAN_LETTERS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue"})
FALLBACK = "stammbaum"


def file_slug(*, text: str) -> str:
    """
    "Familie Gößl" as "familie-goessl" (#34): lower case, the German letters spelled out, any other letter without
    its accent and everything else a dash - a name that works on every disk and in a download's header.
    "stammbaum" for a text with nothing left of it, "Ахнен" for instance.
    """
    folded = unicodedata.normalize("NFKD", text.casefold().translate(GERMAN_LETTERS))
    return re.sub(r"[^a-z0-9]+", "-", folded.encode("ascii", "ignore").decode()).strip("-") or FALLBACK
