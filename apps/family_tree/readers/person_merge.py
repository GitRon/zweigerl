"""
What merging two people (#85) shows before anything happens: whom the search offers, and the two side by side.
The merge itself is "actions.person_merge".
"""

from dataclasses import dataclass

from apps.family_tree.domain.relationship import ancestors, descendants
from apps.family_tree.models import ParentChild, Person
from apps.family_tree.models.person import NAME_AND_STATUS_FIELDS
from apps.family_tree.readers.evidence import facts, sources
from apps.family_tree.readers.person import PersonListEntry, person_entries, person_list, relative_groups
from apps.family_tree.readers.relationship import family_graph


def merge_candidates(*, pk: int, search: str) -> list[PersonListEntry]:
    """
    Whom the search offers to merge with "pk" (#85): everybody whose name matches, sorted by family name - but
    not the person, their partners, their ancestors and their descendants, who are two people by what the tree
    says. Siblings are offered: two people both imports brought are siblings once their parents are merged.
    Nobody before anything is typed, and nobody for a person who is not there.
    """
    if not search or not Person.objects.filter(pk=pk).exists():
        return []

    family = family_graph()
    excluded = {pk, *family.partners.get(pk, ()), *ancestors(family=family, person_id=pk)}
    excluded |= descendants(family=family, person_id=pk)
    return [entry for entry in person_list(search=search).entries if entry.person.pk not in excluded]


@dataclass(frozen=True, kw_only=True)
class MergeField:
    name: str
    label: str
    # What each of the two has, as the card writes it: a choice by its label, an empty name as "".
    text: str
    other_text: str

    @property
    def differs(self) -> bool:
        return self.text != self.other_text


@dataclass(frozen=True, kw_only=True)
class MergeSide:
    entry: PersonListEntry
    # The import the person came from - "PAF Ronny" - None for somebody entered here.
    origin: str | None
    fact_count: int
    photo_count: int
    note_count: int
    source_count: int
    relative_count: int


@dataclass(frozen=True, kw_only=True)
class MergePreview:
    # The person the merge started on, who stays, and the other one, who goes into them.
    person: MergeSide
    other: MergeSide
    fields: list[MergeField]
    # Why the two cannot be one, or "".
    refusal: str = ""

    @property
    def sides(self) -> tuple[MergeSide, MergeSide]:
        # The person, then the other: the columns of the comparison.
        return self.person, self.other


def merge_preview(*, pk: int, other_pk: int) -> MergePreview | None:
    """
    The two side by side before they are merged (#85): their names, sex and status, which of those differ, their
    Lebensdaten and Herkunft, and how much each brings - or why the two cannot be one, as "actions.person_merge"
    refuses them. None for somebody who is not there, and for the person and themselves.
    """
    people = {person.pk: person for person in Person.objects.select_related("gedcom_import").filter(pk__in=(pk, other_pk))}
    if pk == other_pk or pk not in people or other_pk not in people:
        return None

    person, other = people[pk], people[other_pk]
    entries = person_entries(person_ids=[pk, other_pk])
    return MergePreview(
        person=_side(person=person, entry=entries[pk]),
        other=_side(person=other, entry=entries[other_pk]),
        fields=[
            MergeField(
                name=name,
                label=Person._meta.get_field(name).verbose_name,
                text=_text(person=person, name=name),
                other_text=_text(person=other, name=name),
            )
            for name in NAME_AND_STATUS_FIELDS
        ],
        refusal=_refusal(person=person, other=other, names={pk: entries[pk].name, other_pk: entries[other_pk].name}),
    )


def _side(*, person: Person, entry: PersonListEntry) -> MergeSide:
    return MergeSide(
        entry=entry,
        origin=person.gedcom_import.name if person.gedcom_import else None,
        fact_count=facts(person=person).count(),
        photo_count=person.photo_links.count(),
        note_count=person.notes.count(),
        source_count=sources(person=person).count(),
        relative_count=sum(len(group.entries) for group in relative_groups(person=person)),
    )


def _text(*, person: Person, name: str) -> str:
    display = getattr(person, f"get_{name}_display", None)
    return display() if display else getattr(person, name)


def _refusal(*, person: Person, other: Person, names: dict[int, str]) -> str:
    family = family_graph()
    if other.pk in family.partners.get(person.pk, ()):
        return f"{names[person.pk]} und {names[other.pk]} sind ein Paar, also zwei Personen."
    for ancestor, descendant in ((person, other), (other, person)):
        if ancestor.pk in ancestors(family=family, person_id=descendant.pk):
            return f"{names[ancestor.pk]} ist ein Vorfahr von {names[descendant.pk]}, also sind es zwei Personen."

    parents = set(ParentChild.objects.filter(child=person).values_list("parent", flat=True))
    birth_parents = {
        *ParentChild.objects.filter(child=person, pedigree=ParentChild.Pedigree.BIRTH).values_list("parent", flat=True),
        *ParentChild.objects.filter(child=other, pedigree=ParentChild.Pedigree.BIRTH)
        .exclude(parent__in=parents)
        .values_list("parent", flat=True),
    }
    if len(birth_parents) > ParentChild.MAX_BIRTH_PARENTS:
        return (
            f"Zusammen hätten die beiden {len(birth_parents)} leibliche Eltern. Führ zuerst die Eltern zusammen, "
            "die dieselben sind - dann die beiden."
        )
    return ""
