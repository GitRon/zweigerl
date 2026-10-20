"""Turn a real PAF export into the anonymised test file of #32.

    uv run python -m scripts.anonymise_paf <real export> apps/family_tree/tests/data/paf_export.ged

The structure stays: line order, levels, tags, xrefs, BOM, line endings, the charset declaration and the
kind of every value. Every value that says something about real people is replaced - names, places, dates,
free text, file paths, the submitter and the `_UID`s. A tag with a value this script has no rule for stops
the run rather than passing through, and so does any replaced word that is still in the result. Nothing is
written then.

Every run draws its replacements and its date offset at random and keeps them only in memory, so nothing in
the repository leads back to the real values. Within one file they are consistent: the same surname becomes
the same invented surname everywhere, and every date moves by the same number of days.
"""

import argparse
import datetime
import itertools
import random
import re
import secrets
import string
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

BOM = "﻿"
LINE = re.compile(r"(?P<level>\d+) (?:(?P<xref>@[^@]+@) )?(?P<tag>\S+)(?: (?P<value>.*))?")
POINTER = re.compile(r"@[^@]+@")
LETTERS = re.compile(r"[^\W\d_]+")
WORD = re.compile(r"[^\W_]+")
# A path keeps its drive and its extension; the folders and the name in between are what say who it is.
FILE_PATH = re.compile(r"(?P<drive>[A-Za-z]:)?(?P<path>.*?)(?P<extension>\.[^\W_]{1,5})?")

# Below this length a free-text word is too common to count as a leak ("am", "und", "der").
MIN_TEXT_WORD = 4
MIN_NAME_WORD = 2
MAX_ATTEMPTS = 100

NAME_TAGS = {"GIVN": "given", "NICK": "given", "SURN": "surname", "_MARNM": "surname", "_AKA": "name"}
TEXT_TAGS = {
    "ADDR", "ADR1", "ADR2", "AUTH", "CAUS", "CITY", "COPR", "CTRY", "DSCR", "EDUC", "EMAIL", "EVEN", "NATI",
    "NOTE", "OCCU", "PAGE", "PHON", "POST", "PUBL", "RELI", "RESI", "STAE", "TEXT", "TITL", "TYPE",
}  # fmt: skip
# Values that describe the file or a picture's role, never a person. NPFX holds titles such as "Dr.".
KEEP_TAGS = {"CHAR", "DEST", "FORM", "LANG", "NPFX", "SEX", "TIME", "VERS", "_PRIM", "_SCBK", "_SSHOW", "_TYPE"}
CONTINUATION_TAGS = {"CONT", "CONC"}

GEDCOM_MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
GERMAN_MONTHS = [
    "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November",
    "Dezember",
]  # fmt: skip
GERMAN_SHORT_MONTHS = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
# The words a free-text date is built from rather than what it is about: they stay.
DATE_KEYWORDS = {
    "abt", "aft", "and", "bef", "bet", "bis", "ca", "cal", "est", "from", "frühjahr", "frühling", "herbst", "int",
    "nach", "oder", "sommer", "to", "um", "und", "vor", "winter", "zwischen",
}  # fmt: skip

MONTH_PATTERN = "|".join(
    sorted({*GEDCOM_MONTHS, *GERMAN_MONTHS, *GERMAN_SHORT_MONTHS}, key=len, reverse=True),
)
DATE_PARTS = re.compile(
    rf"(?P<numeric>(?P<nd>\d{{1,2}})\.(?P<nm>\d{{1,2}})\.(?P<ny>\d{{4}}))"
    rf"|(?P<full>(?P<fd>\d{{1,2}}) (?P<fm>{MONTH_PATTERN}) (?P<fy>\d{{4}}))(?![^\W\d_])"
    rf"|(?P<month_year>(?<![^\W\d_])(?P<mm>{MONTH_PATTERN}) (?P<my>\d{{4}}))"
    rf"|(?P<day_month>(?P<dd>\d{{1,2}}) (?P<dm>{MONTH_PATTERN}))(?![^\W\d_])"
    rf"|(?P<year>(?<!\d)\d{{4}}(?!\d))"
    rf"|(?P<word>[^\W_]+)",
    re.IGNORECASE,
)

ASCII_LETTERS = string.ascii_lowercase
LATIN1_LETTERS = "äöüáéíóúý"
BEYOND_LATIN1_LETTERS = "čďěňřšťůž"

# Invented replacements, by the kind of letters they hold: plain ASCII, Latin-1 beyond ASCII, and letters
# outside Latin-1, so a name with a háček stays a name with a háček.
FEMALE_NAMES = {
    "ascii": [
        "Agathe", "Amalia", "Apollonia", "Barbara", "Berta", "Crescentia", "Edeltraud", "Elfriede", "Emerenz",
        "Franziska", "Genoveva", "Gertraud", "Hedwig", "Hildegard", "Ida", "Irmgard", "Josepha", "Kunigunde",
        "Leopoldine", "Magdalena", "Mechthild", "Notburga", "Ottilie", "Philomena", "Regina", "Rosalia",
        "Scholastika", "Theresia", "Ursula", "Veronika", "Walburga", "Wilhelmine", "Zita",
    ],
    "latin1": ["Bärbel", "Cäcilie", "Dörte", "Hélène", "Jördis", "Käthe", "Rosalía", "Zoë"],
    "beyond": ["Božena", "Jiřina", "Libuše", "Růžena", "Věra", "Zdeňka"],
}  # fmt: skip
MALE_NAMES = {
    "ascii": [
        "Alois", "Balthasar", "Benedikt", "Cyrill", "Dominikus", "Emmeram", "Engelbert", "Fridolin", "Gebhard",
        "Gottfried", "Gregor", "Hieronymus", "Ignaz", "Isidor", "Kaspar", "Kilian", "Korbinian", "Laurenz",
        "Leonhard", "Magnus", "Melchior", "Nepomuk", "Oswald", "Pankraz", "Quirin", "Remigius", "Rupert",
        "Severin", "Urban", "Valentin", "Vinzenz", "Wendelin", "Xaver", "Zacharias",
    ],
    "latin1": ["André", "Björn", "Jörg", "José", "Jürgen", "René", "Sören", "Thaddäus"],
    "beyond": ["Bořivoj", "Dušan", "Jiří", "Luboš", "Lukáš", "Matěj", "Přemysl", "Tomáš"],
}  # fmt: skip
SURNAMES = {
    "ascii": [
        "Aichinger", "Brandstetter", "Eberharter", "Fasching", "Gstettner", "Haslinger", "Irrgang", "Kammerlander",
        "Kronberger", "Leitgeb", "Mairhofer", "Niederreiter", "Oberlechner", "Pichlmayr", "Rainalter",
        "Schwaighofer", "Stockinger", "Tschurtschenthaler", "Unterberger", "Vogelsang", "Wimmesberger",
        "Zehetner",
    ],
    "latin1": [
        "Böckl", "Fürstauer", "Gößl", "Grünwalder", "Höllerer", "Krämerl", "Mößlacher", "Schützenhofer",
        "Söllner", "Strauß", "Weißhäupl",
    ],
    "beyond": ["Černík", "Dvořák", "Hrubeš", "Kovář", "Kučera", "Pešek", "Růžička", "Šimek", "Žák"],
}  # fmt: skip
PLACE_PREFIXES = {
    "ascii": ["Alt", "Berg", "Eich", "Hasel", "Kirch", "Lind", "Neu", "Ober", "Rot", "Stein", "Unter", "Wald"],
    "latin1": ["Bärn", "Fürst", "Göß", "Grün", "Hör", "Mühl", "Schön"],
}  # fmt: skip
PLACE_SUFFIXES = [
    "au", "bach", "brunn", "dorf", "feld", "heim", "hofen", "ing", "kirchen", "leiten", "reuth", "stetten", "wang",
    "zell",
]  # fmt: skip
BEYOND_LATIN1_PLACES = ["Bělčice", "Hořenice", "Křemže", "Lužná", "Řečice", "Šumná", "Žďárek"]


class AnonymiseError(Exception):
    """The export cannot be anonymised safely, so nothing is written."""


@dataclass(kw_only=True)
class Line:
    level: int
    xref: str | None
    tag: str
    value: str | None

    def render(self) -> str:
        xref = f"{self.xref} " if self.xref else ""
        value = "" if self.value is None else f" {self.value}"
        return f"{self.level} {xref}{self.tag}{value}"


@dataclass(kw_only=True)
class Unit:
    """A line with a value, the rule for it and the CONT and CONC lines that carry it on."""

    rule: str
    indexes: list[int]
    sex: str


@dataclass(kw_only=True)
class Document:
    lines: list[Line]
    bom: bool
    newline: str
    trailing_newline: bool

    def render(self) -> str:
        text = self.newline.join(line.render() for line in self.lines)
        if self.trailing_newline:
            text += self.newline
        return (BOM if self.bom else "") + text


def parse(*, text: str) -> Document:
    bom = text.startswith(BOM)
    text = text.removeprefix(BOM)
    newline = "\r\n" if "\r\n" in text else "\n"
    rows = text.split(newline)
    trailing_newline = rows[-1] == ""
    if trailing_newline:
        rows.pop()
    lines = []
    for number, row in enumerate(rows, start=1):
        match = LINE.fullmatch(row)
        if match is None:
            raise AnonymiseError(f"Line {number} is not a GEDCOM line.")
        lines.append(Line(level=int(match["level"]), xref=match["xref"], tag=match["tag"], value=match["value"]))
    return Document(lines=lines, bom=bom, newline=newline, trailing_newline=trailing_newline)


def char_class(*, text: str) -> str:
    if any(ord(char) > 0xFF for char in text):
        return "beyond"
    if any(ord(char) > 0x7F for char in text):
        return "latin1"
    return "ascii"


def rule_for(*, path: list[str], value: str | None) -> str:
    """Which replacement a value gets, by the tags above it. Unknown values stop the run."""
    tag = path[-1]
    if not value or POINTER.fullmatch(value):
        return "keep"
    # The program that wrote the file, its name and its publisher's address, says nothing about the family.
    if path[:2] == ["HEAD", "SOUR"]:
        return "keep"
    if path[0] == "SUBM":
        return "text"
    if tag == "NAME" and path[0] == "INDI":
        return "name"
    rule = NAME_TAGS.get(tag) or {"PLAC": "place", "DATE": "date", "FILE": "file", "_UID": "uid"}.get(tag)
    if rule:
        return rule
    if tag in TEXT_TAGS:
        return "text"
    if tag in KEEP_TAGS or value == "Y":
        return "keep"
    raise AnonymiseError(f"No rule for a value of {'/'.join(path)}.")


def record_sexes(*, lines: list[Line]) -> dict[int, str]:
    """The SEX of every record, by the index of its level-0 line - PAF writes it after the NAME."""
    sexes = {}
    record = 0
    for index, line in enumerate(lines):
        if line.level == 0:
            record = index
        elif line.level == 1 and line.tag == "SEX":
            sexes[record] = line.value
    return sexes


def units(*, lines: list[Line]) -> Iterator[Unit]:
    sexes = record_sexes(lines=lines)
    path: list[str] = []
    record = 0
    rules: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.level == 0:
            record = index
        path = [*path[: line.level], line.tag]
        rules = rules[: line.level]
        if line.tag in CONTINUATION_TAGS and rules and rules[-1] == "text":
            # A CONT or CONC that does not follow its line directly still carries on its text.
            rules.append("text")
            yield Unit(rule="text" if line.value else "keep", indexes=[index], sex="")
            index += 1
            continue
        rule = rule_for(path=path, value=line.value)
        rules.append(rule)
        indexes = continued(lines=lines, index=index) if rule == "text" else [index]
        yield Unit(rule=rule, indexes=indexes, sex=sexes.get(record, ""))
        index = indexes[-1] + 1


def continued(*, lines: list[Line], index: int) -> list[int]:
    """A line with the CONT and CONC lines right below it."""
    indexes = [index]
    level = lines[index].level + 1
    while indexes[-1] + 1 < len(lines):
        following = lines[indexes[-1] + 1]
        if following.tag not in CONTINUATION_TAGS or following.level != level:
            break
        indexes.append(indexes[-1] + 1)
    return indexes


def joined_text(*, lines: list[Line], indexes: list[int]) -> str:
    """A value with its CONT and CONC lines, as one text: CONT is a line break, CONC goes on mid-word."""
    text = lines[indexes[0]].value or ""
    for index in indexes[1:]:
        separator = "\n" if lines[index].tag == "CONT" else ""
        text += separator + (lines[index].value or "")
    return text


def split_text(*, lines: list[Line], indexes: list[int], text: str) -> None:
    """Cut a same-length replacement back into the lines it came from, at the same places."""
    position = 0
    for index in indexes:
        line = lines[index]
        if line.tag == "CONT" and index != indexes[0]:
            position += 1
        length = len(line.value or "")
        if line.value is not None:
            line.value = text[position : position + length]
        position += length


def words(*, text: str, pattern: re.Pattern[str], min_length: int) -> set[str]:
    return {word.casefold() for word in pattern.findall(text) if len(word) >= min_length}


def month_names() -> set[str]:
    return {month.casefold() for month in [*GEDCOM_MONTHS, *GERMAN_MONTHS, *GERMAN_SHORT_MONTHS]}


def forbidden_words(*, document: Document) -> set[str]:
    """Every word the replacement must not leave behind - and that no invented value may happen to be."""
    forbidden: set[str] = set()
    kept: set[str] = set()
    for unit in units(lines=document.lines):
        text = joined_text(lines=document.lines, indexes=unit.indexes)
        if unit.rule in {"name", "given", "surname", "place"}:
            forbidden |= words(text=text, pattern=LETTERS, min_length=MIN_NAME_WORD)
        elif unit.rule in {"text", "date"}:
            forbidden |= words(text=text, pattern=LETTERS, min_length=MIN_TEXT_WORD)
        elif unit.rule == "file":
            path = FILE_PATH.fullmatch(text)["path"]
            forbidden |= words(text=path, pattern=LETTERS, min_length=MIN_TEXT_WORD)
        elif unit.rule == "keep":
            kept |= words(text=text, pattern=LETTERS, min_length=1)
    return forbidden - kept - DATE_KEYWORDS - month_names()


class Anonymiser:
    def __init__(self, *, rng: random.Random, forbidden: set[str], offset_days: int) -> None:
        self.rng = rng
        self.forbidden = forbidden
        self.offset_days = offset_days
        self.offset_months = round(self.offset_days / 30.436875)
        self.offset_years = round(self.offset_days / 365.2425)
        self.mappings: dict[tuple[str, ...], str] = {}
        self.used: set[str] = set()

    def anonymise(self, *, document: Document) -> None:
        for unit in units(lines=document.lines):
            if unit.rule == "keep":
                continue
            text = joined_text(lines=document.lines, indexes=unit.indexes)
            if unit.rule == "text":
                split_text(lines=document.lines, indexes=unit.indexes, text=self.text(value=text))
                continue
            replace = {
                "name": self.name,
                "given": self.given,
                "surname": self.surname,
                "place": self.place,
                "date": self.date,
                "file": self.file,
                "uid": self.uid,
            }[unit.rule]
            document.lines[unit.indexes[0]].value = replace(value=text, sex=unit.sex)

    def remembered(self, *, key: tuple[str, ...], invent: Callable[[], str]) -> str:
        if key not in self.mappings:
            self.mappings[key] = invent()
        return self.mappings[key]

    def allowed(self, *, candidate: str) -> bool:
        return not words(text=candidate, pattern=LETTERS, min_length=1) & self.forbidden

    def choose(self, *, candidates: list[str], original: str) -> str:
        allowed = [candidate for candidate in candidates if self.allowed(candidate=candidate)]
        if not allowed:
            return self.scramble(word=original)
        # Two real names share an invented one only once every invented one is taken.
        chosen = self.rng.choice([candidate for candidate in allowed if candidate not in self.used] or allowed)
        self.used.add(chosen)
        return chosen.upper() if original.isupper() and len(original) > 1 else chosen

    def scramble_char(self, *, char: str) -> str:
        if char.isdigit():
            return self.rng.choice(string.digits)
        if not char.isalpha() or char == "ß":
            return char
        alphabet = {"ascii": ASCII_LETTERS, "latin1": LATIN1_LETTERS, "beyond": BEYOND_LATIN1_LETTERS}
        replacement = self.rng.choice(alphabet[char_class(text=char)])
        return replacement if char.islower() else replacement.upper()

    def scramble(self, *, word: str) -> str:
        """A word of the same length and the same kinds of letters, digits and case."""
        for _attempt in range(MAX_ATTEMPTS):
            candidate = "".join(self.scramble_char(char=char) for char in word)
            if self.allowed(candidate=candidate):
                return candidate
        raise AnonymiseError(f"No replacement found for a word of {len(word)} characters.")

    def word(self, *, word: str) -> str:
        return self.remembered(key=("word", word), invent=lambda: self.scramble(word=word))

    def text(self, *, value: str) -> str:
        return WORD.sub(lambda match: self.word(word=match[0]), value)

    def given(self, *, value: str, sex: str) -> str:
        pools = {"F": [FEMALE_NAMES], "M": [MALE_NAMES]}.get(sex, [FEMALE_NAMES, MALE_NAMES])

        def invent(*, token: str) -> str:
            candidates = [name for pool in pools for name in pool[char_class(text=token)]]
            return self.choose(candidates=candidates, original=token)

        return LETTERS.sub(
            lambda match: self.remembered(key=("given", sex, match[0]), invent=lambda: invent(token=match[0])), value
        )

    def surname(self, *, value: str, sex: str = "") -> str:
        return LETTERS.sub(
            lambda match: self.remembered(
                key=("surname", match[0]),
                invent=lambda: self.choose(candidates=SURNAMES[char_class(text=match[0])], original=match[0]),
            ),
            value,
        )

    def name(self, *, value: str, sex: str) -> str:
        """`Given /Surname/ suffix`: the part between the slashes is the surname, `//` and `/?/` stay."""
        given, slash, rest = value.partition("/")
        if not slash:
            return self.given(value=value, sex=sex)
        surname, closing, suffix = rest.partition("/")
        return (
            self.given(value=given, sex=sex)
            + slash
            + self.surname(value=surname)
            + closing
            + self.given(value=suffix, sex=sex)
        )

    def invent_place(self, *, part: str) -> str:
        kind = char_class(text=part)
        if kind == "beyond":
            candidates = BEYOND_LATIN1_PLACES
        else:
            candidates = [prefix + suffix for prefix, suffix in itertools.product(PLACE_PREFIXES[kind], PLACE_SUFFIXES)]
        return self.choose(candidates=candidates, original=part)

    def place(self, *, value: str, sex: str = "") -> str:
        """Every comma part becomes an invented place, so the number of parts stays."""
        parts = []
        for part in value.split(","):
            name = part.strip()
            if not LETTERS.search(name):
                # A part of digits only - a house number, a district - gets other digits.
                parts.append(self.text(value=part))
                continue
            invented = self.remembered(key=("place", name), invent=lambda name=name: self.invent_place(part=name))
            parts.append(part.replace(name, invented, 1))
        return ",".join(parts)

    def file(self, *, value: str, sex: str = "") -> str:
        parts = FILE_PATH.fullmatch(value)
        return (parts["drive"] or "") + self.text(value=parts["path"]) + (parts["extension"] or "")

    def uid(self, *, value: str, sex: str = "") -> str:
        def invent() -> str:
            return "".join(self.hex_digit(like=char) if char in string.hexdigits else char for char in value)

        return self.remembered(key=("uid", value), invent=invent)

    def hex_digit(self, *, like: str) -> str:
        digit = self.rng.choice("0123456789ABCDEF")
        return digit.lower() if like.islower() else digit

    def date(self, *, value: str, sex: str = "") -> str:
        return DATE_PARTS.sub(lambda match: self.date_part(match=match), value)

    def date_part(self, *, match: re.Match[str]) -> str:
        if match["numeric"]:
            day, month, year = self.shift_day(year=int(match["ny"]), month=int(match["nm"]), day=int(match["nd"]))
            return f"{str(day).zfill(len(match['nd']))}.{str(month).zfill(len(match['nm']))}.{year}"
        if match["full"]:
            day, month, year = self.shift_day(
                year=int(match["fy"]), month=month_index(name=match["fm"]), day=int(match["fd"])
            )
            return f"{str(day).zfill(len(match['fd']))} {month_name(like=match['fm'], index=month)} {year}"
        if match["month_year"]:
            months = int(match["my"]) * 12 + month_index(name=match["mm"]) - 1 + self.offset_months
            return f"{month_name(like=match['mm'], index=months % 12 + 1)} {months // 12}"
        if match["day_month"]:
            day, month, _year = self.shift_day(year=None, month=month_index(name=match["dm"]), day=int(match["dd"]))
            return f"{str(day).zfill(len(match['dd']))} {month_name(like=match['dm'], index=month)}"
        if match["year"]:
            return str(int(match["year"]) + self.offset_years)
        word = match["word"]
        if word.casefold() in DATE_KEYWORDS:
            return word
        return self.word(word=word)

    def shift_day(self, *, year: int | None, month: int, day: int) -> tuple[int, int, int]:
        """A day moved by the offset. Without a year, it moves within a year that has the day."""
        base_year = year or (2000 if (month, day) == (2, 29) else 2001)
        try:
            shifted = datetime.date(base_year, month, day) + datetime.timedelta(days=self.offset_days)
        except ValueError:
            months = base_year * 12 + month - 1 + self.offset_months
            return day, months % 12 + 1, months // 12
        return shifted.day, shifted.month, shifted.year


def month_index(*, name: str) -> int:
    """1 to 12 for a month name `DATE_PARTS` found, in any of the three spellings."""
    return {
        month.casefold(): index
        for months in (GEDCOM_MONTHS, GERMAN_SHORT_MONTHS, GERMAN_MONTHS)
        for index, month in enumerate(months, start=1)
    }[name.casefold()]


def month_name(*, like: str, index: int) -> str:
    """The month in the language, length and case of the one it replaces."""
    folded = like.casefold()
    if folded in {month.casefold() for month in GEDCOM_MONTHS}:
        name = GEDCOM_MONTHS[index - 1]
        return name if like.isupper() else name.title()
    short = GERMAN_SHORT_MONTHS[index - 1]
    # "Jun" would read as the GEDCOM month, so a German short name that is one becomes the full name.
    if folded in {month.casefold() for month in GERMAN_SHORT_MONTHS} and short.upper() not in GEDCOM_MONTHS:
        return short
    return GERMAN_MONTHS[index - 1]


def refuse_leaks(*, document: Document, forbidden: set[str]) -> None:
    """Checked value by value with its CONC lines joined: the end of a word cut by CONC is no word of its own."""
    found: set[str] = set()
    for unit in units(lines=document.lines):
        # A new _UID is random hex, whose letters spell a word only by chance.
        if unit.rule != "uid":
            text = joined_text(lines=document.lines, indexes=unit.indexes)
            found |= words(text=text, pattern=LETTERS, min_length=1) & forbidden
    if found:
        raise AnonymiseError(f"{len(found)} replaced words are still in the result: {', '.join(sorted(found))}.")


def anonymise(*, text: str, rng: random.Random) -> str:
    document = parse(text=text)
    forbidden = forbidden_words(document=document)
    # Ten to thirty years back: far enough that no real date shows, near enough that the years stay plausible.
    offset_days = rng.randint(-30 * 365, -10 * 365)
    Anonymiser(rng=rng, forbidden=forbidden, offset_days=offset_days).anonymise(document=document)
    refuse_leaks(document=document, forbidden=forbidden)
    return document.render()


def main(*, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write an anonymised copy of a PAF export.")
    parser.add_argument("source", type=Path, help="the real export, outside the repository")
    parser.add_argument("target", type=Path, help="where the anonymised file goes")
    arguments = parser.parse_args(argv)
    try:
        result = anonymise(text=arguments.source.read_bytes().decode("utf-8"), rng=random.Random(secrets.randbits(128)))
    except AnonymiseError as error:
        print(f"Nothing written: {error}", file=sys.stderr)
        return 1
    arguments.target.write_bytes(result.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
