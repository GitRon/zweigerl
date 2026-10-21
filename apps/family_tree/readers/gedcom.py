"""
The export of the whole tree as GEDCOM 5.5.1 (#26). What maps to what is docs/patterns/gedcom.md; writing the
lines is "domain.gedcom".
"""

from collections import defaultdict
from dataclasses import dataclass, field
from itertools import zip_longest
from pathlib import PurePosixPath

from django.db.models import Prefetch, QuerySet
from django.utils.timezone import localdate

from apps.family_tree.domain.dates import DateKind, Precision, UncertainDate, to_gedcom
from apps.family_tree.domain.gedcom import Node, from_raw, write
from apps.family_tree.models import (
    Citation,
    Fact,
    ParentChild,
    Partnership,
    Person,
    Photo,
    PhotoPerson,
    SiblingPair,
    Source,
    TreeSettings,
)

# The event or attribute each kind of fact becomes. A birthplace is the PLAC of a BIRT, a residence the PLAC of a
# RESI; the other value kinds carry their value on the line itself.
DATE_TAGS = {
    Fact.Kind.BIRTH: "BIRT",
    Fact.Kind.BAPTISM: "CHR",
    Fact.Kind.DEATH: "DEAT",
    Fact.Kind.BURIAL: "BURI",
    Fact.Kind.MARRIAGE: "MARR",
    Fact.Kind.DIVORCE: "DIV",
}
VALUE_TAGS = {Fact.Kind.OCCUPATION: "OCCU", Fact.Kind.EDUCATION: "EDUC", Fact.Kind.NATIONALITY: "NATI"}

# What GEDCOM 5.5.1 has no tag for, under tags of Zweigerl's own - each written only when it is not the default,
# so a tree entered the plain way exports as plain GEDCOM.
RELIABILITY_TAG = "_ZWG_RELIABILITY"
KIND_TAG = "_ZWG_KIND"
STATUS_TAG = "_ZWG_STATUS"


@dataclass(kw_only=True)
class _Family:
    """
    One FAM: a partnership, a parent with the children no partnership is named for, or two siblings whose parents
    nobody knows.
    """

    xref: str
    parents: list[Person]
    # The links of each child into this family, by the child's id.
    children: dict[int, list[ParentChild]] = field(default_factory=dict)
    partnership: Partnership | None = None
    sibling_pair: SiblingPair | None = None


def gedcom_export() -> str:
    """
    The whole tree as GEDCOM 5.5.1 in UTF-8: everybody, with their facts and citations, their families, the
    sources with their files and the photos - and what an import kept raw, written back. The home person comes
    first, so an import into an empty tree (#22) makes them the home person again. #27's backup calls this too.
    """
    people = _people()
    families = _families(people=people)
    # Who is a parent and who a child in which family, once - a search per person would take minutes on a large tree.
    as_parent, as_child = defaultdict(list), defaultdict(list)
    for family in families:
        for parent in family.parents:
            as_parent[parent.pk].append(family)
        for child_id in family.children:
            as_child[child_id].append(family)
    return write(
        records=[
            _header(),
            Node(xref="@U1@", tag="SUBM", children=(Node(tag="NAME", value="Zweigerl"),)),
            *(
                _individual(person=person, as_parent=as_parent[person.pk], as_child=as_child[person.pk])
                for person in people.values()
            ),
            *(_family(family=family) for family in families),
            *(_source(source=source) for source in Source.objects.prefetch_related("files").order_by("pk")),
            *(_photo(photo=photo) for photo in Photo.objects.order_by("pk")),
            Node(tag="TRLR"),
        ]
    )


def _people() -> dict[int, Person]:
    """
    Everybody by id, the home person first and the others in the order they were entered.
    """
    home_id = TreeSettings.objects.filter(pk=TreeSettings.ONLY_ROW).values_list("home_person_id", flat=True).first()
    people = Person.objects.prefetch_related(
        Prefetch("facts", queryset=_facts()),
        Prefetch("filed_sources", queryset=Source.objects.order_by("pk")),
        Prefetch("photo_links", queryset=PhotoPerson.objects.order_by("photo_id")),
    ).order_by("pk")
    return {person.pk: person for person in sorted(people, key=lambda person: person.pk != home_id)}


def _facts() -> QuerySet[Fact]:
    return Fact.objects.prefetch_related(Prefetch("citations", queryset=Citation.objects.order_by("pk")))


def _families(*, people: dict[int, Person]) -> list[_Family]:
    families = {
        partnership.pk: _Family(
            xref=f"@F{partnership.pk}@",
            parents=_couple(person_a=people[partnership.person_a_id], person_b=people[partnership.person_b_id]),
            partnership=partnership,
        )
        for partnership in Partnership.objects.prefetch_related(Prefetch("facts", queryset=_facts())).order_by("pk")
    }
    single_parents: dict[int, _Family] = {}
    for link in ParentChild.objects.order_by("child_id", "pk"):
        if link.partnership_id is not None:
            family = families[link.partnership_id]
        else:
            family = single_parents.setdefault(
                link.parent_id, _Family(xref=f"@FP{link.parent_id}@", parents=[people[link.parent_id]])
            )
        family.children.setdefault(link.child_id, []).append(link)
    siblings = [
        _Family(
            xref=f"@FS{pair.pk}@", parents=[], children={pair.person_a_id: [], pair.person_b_id: []}, sibling_pair=pair
        )
        for pair in SiblingPair.objects.order_by("pk")
    ]
    return [*families.values(), *sorted(single_parents.values(), key=lambda family: family.parents[0].pk), *siblings]


def _couple(*, person_a: Person, person_b: Person) -> list[Person]:
    """
    The two partners as HUSB and WIFE. GEDCOM 5.5.1 knows no other roles, so a woman is the WIFE whenever the
    other one is not a woman too, and otherwise the order the partnership was entered in decides.
    """
    if person_a.sex == Person.Sex.FEMALE and person_b.sex != Person.Sex.FEMALE:
        return [person_b, person_a]
    return [person_a, person_b]


def _header() -> Node:
    today = UncertainDate(kind=DateKind.EXACT, date_1=localdate(), precision=Precision.DAY)
    return Node(
        tag="HEAD",
        children=(
            Node(tag="SOUR", value="ZWEIGERL", children=(Node(tag="NAME", value="Zweigerl"),)),
            Node(tag="DATE", value=to_gedcom(date=today)),
            Node(tag="SUBM", pointer="@U1@"),
            Node(
                tag="GEDC",
                children=(Node(tag="VERS", value="5.5.1"), Node(tag="FORM", value="LINEAGE-LINKED")),
            ),
            Node(tag="CHAR", value="UTF-8"),
        ),
    )


def _individual(*, person: Person, as_parent: list[_Family], as_child: list[_Family]) -> Node:
    facts = list(person.facts.all())
    # The parts of a name an import kept raw - a title, a married name - belong below the NAME, not the INDI.
    name_parts = [record for record in person.gedcom_raw if record["tag"] == "NAME" and not record.get("value")]
    return Node(
        xref=f"@I{person.pk}@",
        tag="INDI",
        children=(
            *_name(person=person, raw=name_parts),
            Node(tag="SEX", value=person.sex),
            *_events(facts=facts),
            *_status(person=person, facts=facts),
            *(Node(tag="FAMS", pointer=family.xref) for family in as_parent),
            *(_child_of(family=family, links=family.children[person.pk]) for family in as_child),
            *(Node(tag="SOUR", pointer=f"@S{source.pk}@") for source in person.filed_sources.all()),
            *(_photo_link(link=link) for link in person.photo_links.all()),
            *from_raw(records=[record for record in person.gedcom_raw if record not in name_parts]),
        ),
    )


def _name(*, person: Person, raw: list[dict]) -> tuple[Node, ...]:
    """
    The NAME with GIVN, SURN and NICK, and below them what an import kept raw of the name it read.
    """
    kept = tuple(node for record in raw for node in from_raw(records=record.get("children", [])))
    if not (person.given_names or person.surname or person.call_name or kept):
        return ()
    parts = (
        Node(tag="GIVN", value=person.given_names),
        Node(tag="SURN", value=person.surname),
        Node(tag="NICK", value=person.call_name),
    )
    full = f"{person.given_names} /{person.surname}/".strip()
    return (Node(tag="NAME", value=full, children=(*(part for part in parts if part.value), *kept)),)


def _events(*, facts: list[Fact]) -> list[Node]:
    """
    A person's facts as events and attributes. The first birth and the first birthplace are one BIRT again, the
    way GEDCOM keeps them; a second one of either is a BIRT of its own.
    """
    births = [fact for fact in facts if fact.kind == Fact.Kind.BIRTH]
    places = [fact for fact in facts if fact.kind == Fact.Kind.BIRTHPLACE]
    others = [fact for fact in facts if fact.kind not in (Fact.Kind.BIRTH, Fact.Kind.BIRTHPLACE)]
    return [
        *(_birth(birth=birth, place=place) for birth, place in zip_longest(births, places)),
        *(_event(fact=fact) for fact in others),
    ]


def _birth(*, birth: Fact | None, place: Fact | None) -> Node:
    """
    One BIRT from a birth date and a birthplace, either of them may be missing. How sure the place is stays with
    the PLAC; the citations of both hang below the BIRT, since GEDCOM 5.5.1 has none on a place.
    """
    parts = [fact for fact in (birth, place) if fact is not None]
    date = _date(fact=birth) if birth else ()
    plac = (Node(tag="PLAC", value=place.value, children=_reliability(fact=place)),) if place else ()
    return Node(
        tag="BIRT",
        children=(
            *date,
            *plac,
            *(_reliability(fact=birth) if birth else ()),
            *(_citation(citation=citation) for fact in parts for citation in fact.citations.all()),
            *(node for fact in parts for node in from_raw(records=fact.gedcom_raw)),
        ),
    )


def _event(*, fact: Fact) -> Node:
    """
    Any fact but a birth and a birthplace - of a person or of a couple.
    """
    if fact.kind == Fact.Kind.CUSTOM:
        head = [Node(tag="TYPE", value=fact.label)]
        return Node(tag="EVEN", value=fact.value, children=(*head, *_date(fact=fact), *_details(fact=fact)))
    if fact.kind == Fact.Kind.RESIDENCE:
        return Node(tag="RESI", children=(Node(tag="PLAC", value=fact.value), *_details(fact=fact)))
    if fact.kind in VALUE_TAGS:
        return Node(tag=VALUE_TAGS[fact.kind], value=fact.value, children=_details(fact=fact))
    return Node(tag=DATE_TAGS[fact.kind], children=(*_date(fact=fact), *_details(fact=fact)))


def _date(*, fact: Fact) -> tuple[Node, ...]:
    return (Node(tag="DATE", value=to_gedcom(date=fact.date)),) if fact.date else ()


def _details(*, fact: Fact) -> tuple[Node, ...]:
    """
    What hangs below every fact: how sure it is, its citations, and what an import kept raw.
    """
    return (
        *_reliability(fact=fact),
        *(_citation(citation=citation) for citation in fact.citations.all()),
        *from_raw(records=fact.gedcom_raw),
    )


def _reliability(*, fact: Fact) -> tuple[Node, ...]:
    if fact.reliability == Fact.Reliability.DOCUMENTED:
        return ()
    return (Node(tag=RELIABILITY_TAG, value=fact.reliability),)


def _citation(*, citation: Citation) -> Node:
    page = (Node(tag="PAGE", value=citation.page),) if citation.page else ()
    return Node(
        tag="SOUR", pointer=f"@S{citation.source_id}@", children=(*page, *from_raw(records=citation.gedcom_raw))
    )


def _status(*, person: Person, facts: list[Fact]) -> tuple[Node, ...]:
    """
    "living_status", which GEDCOM has no field for: somebody deceased without a recorded death is "DEAT Y", and
    "living" is a tag of Zweigerl's own - "unknown" is the default and says nothing.
    """
    if person.living_status == Person.LivingStatus.LIVING:
        return (Node(tag=STATUS_TAG, value=person.living_status),)
    if (
        person.living_status == Person.LivingStatus.DECEASED
        and not any(fact.kind == Fact.Kind.DEATH for fact in facts)
        and not _kept_raw(raw=person.gedcom_raw, tag="DEAT")
    ):
        return (Node(tag="DEAT", value="Y"),)
    return ()


def _kept_raw(*, raw: list[dict], tag: str) -> bool:
    """
    Whether an import kept a structure of this tag raw - a wedding with a date Zweigerl could not read says more
    than a "MARR Y" would.
    """
    return any(record["tag"] == tag for record in raw)


def _child_of(*, family: _Family, links: list[ParentChild]) -> Node:
    """
    The FAMC of a child, with the PEDI its parent links agree on. Two parents with different pedigrees - the
    mother's son, adopted by her husband - are told apart on the CHIL of the family instead.
    """
    pedigrees = {link.pedigree for link in links}
    pedigree = (
        (Node(tag="PEDI", value=links[0].pedigree),)
        if len(pedigrees) == 1 and links[0].pedigree != ParentChild.Pedigree.UNKNOWN
        else ()
    )
    raw = (node for link in links for node in from_raw(records=link.gedcom_raw))
    return Node(tag="FAMC", pointer=family.xref, children=(*pedigree, *raw))


def _photo_link(*, link: PhotoPerson) -> Node:
    portrait = (Node(tag="_PRIM", value="Y"),) if link.is_portrait else ()
    return Node(tag="OBJE", pointer=f"@O{link.photo_id}@", children=portrait)


def _family(*, family: _Family) -> Node:
    children = tuple(
        _child(child_id=child_id, links=links, family=family) for child_id, links in sorted(family.children.items())
    )
    return Node(
        xref=family.xref,
        tag="FAM",
        children=(*_parents(family=family), *_couple_facts(family=family), *children, *_family_raw(family=family)),
    )


def _parents(*, family: _Family) -> tuple[Node, ...]:
    """
    HUSB and WIFE of a couple, as "_couple" ordered them; a parent on their own is the one their sex says.
    """
    if len(family.parents) == 2:
        husband, wife = family.parents
        return (Node(tag="HUSB", pointer=f"@I{husband.pk}@"), Node(tag="WIFE", pointer=f"@I{wife.pk}@"))
    return tuple(Node(tag=_role(person=parent), pointer=f"@I{parent.pk}@") for parent in family.parents)


def _role(*, person: Person) -> str:
    return "WIFE" if person.sex == Person.Sex.FEMALE else "HUSB"


def _couple_facts(*, family: _Family) -> tuple[Node, ...]:
    """
    The kind of a partnership and its facts. A marriage nobody has a date for yet is still a marriage: "MARR Y".
    """
    partnership = family.partnership
    if partnership is None:
        return ()
    facts = list(partnership.facts.all())
    kind = (Node(tag=KIND_TAG, value=partnership.kind),) if partnership.kind == Partnership.Kind.COHABITATION else ()
    married = (
        (Node(tag="MARR", value="Y"),)
        if partnership.kind == Partnership.Kind.MARRIAGE
        and not any(fact.kind == Fact.Kind.MARRIAGE for fact in facts)
        and not _kept_raw(raw=partnership.gedcom_raw, tag="MARR")
        else ()
    )
    return (*kind, *married, *(_event(fact=fact) for fact in facts))


def _child(*, child_id: int, links: list[ParentChild], family: _Family) -> Node:
    """
    One CHIL. Where the two parents' links differ in their pedigree, the father's is "_FREL" and the mother's
    "_MREL", as other programs write it.
    """
    pedigrees = {link.parent_id: link.pedigree for link in links}
    relations = ()
    if len(set(pedigrees.values())) > 1:
        husband, wife = family.parents
        relations = (
            Node(tag="_FREL", value=pedigrees[husband.pk]),
            Node(tag="_MREL", value=pedigrees[wife.pk]),
        )
    return Node(tag="CHIL", pointer=f"@I{child_id}@", children=relations)


def _family_raw(*, family: _Family) -> tuple[Node, ...]:
    record = family.partnership or family.sibling_pair
    return from_raw(records=record.gedcom_raw) if record else ()


def _source(*, source: Source) -> Node:
    text = (Node(tag="TEXT", value=source.description),) if source.description else ()
    kind = (Node(tag=KIND_TAG, value=source.kind),) if source.kind != Source.Kind.OTHER else ()
    files = (_file(name=source_file.file.name) for source_file in source.files.all())
    return Node(
        xref=f"@S{source.pk}@",
        tag="SOUR",
        children=(
            Node(tag="TITL", value=source.title),
            *text,
            *kind,
            *(Node(tag="OBJE", children=(file,)) for file in files),
            *from_raw(records=source.gedcom_raw),
        ),
    )


def _photo(*, photo: Photo) -> Node:
    date = (Node(tag="_DATE", value=to_gedcom(date=photo.date)),) if photo.date else ()
    return Node(
        xref=f"@O{photo.pk}@", tag="OBJE", children=(_file(name=photo.file.name, title=photo.description), *date)
    )


def _file(*, name: str, title: str = "") -> Node:
    """
    A FILE with its FORM and, for a photo, what it shows as its TITL. The path is the one in the media
    directory: ids and roles, never a name - see docs/patterns/data-storage.md.
    """
    form = Node(tag="FORM", value=PurePosixPath(name).suffix.lstrip("."))
    titled = (Node(tag="TITL", value=title),) if title else ()
    return Node(tag="FILE", value=name, children=(form, *titled))
