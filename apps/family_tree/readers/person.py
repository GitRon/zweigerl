from collections.abc import Iterable
from dataclasses import dataclass

from django.db.models import Prefetch, Q, QuerySet

from apps.family_tree.domain.dates import date_text, lifespan
from apps.family_tree.domain.names import display_name, initials, matches, sort_key
from apps.family_tree.domain.relationship import relationship_name
from apps.family_tree.models import Citation, Fact, Person, SiblingPair
from apps.family_tree.readers.evidence import facts
from apps.family_tree.readers.relationship import family_graph
from apps.family_tree.readers.tree_settings import home_person


@dataclass(frozen=True, kw_only=True)
class Relatives:
    parents: list[Person]
    partners: list[Person]
    children: list[Person]
    siblings: list[Person]


def relatives(*, person: Person) -> Relatives:
    """
    Everyone directly related to "person", each list in the people's own order. Siblings are those who share
    a parent with them, plus the ones stored explicitly because no shared parent is known - see
    docs/patterns/family.md.
    """
    parents = Person.objects.filter(child_links__child=person)
    siblings = Person.objects.filter(
        Q(parent_links__parent__in=parents)
        | Q(pk__in=SiblingPair.objects.filter(person_b=person).values("person_a"))
        | Q(pk__in=SiblingPair.objects.filter(person_a=person).values("person_b"))
    )

    return Relatives(
        parents=list(parents),
        partners=list(
            Person.objects.filter(
                Q(partnerships_as_a__person_b=person) | Q(partnerships_as_b__person_a=person)
            ).distinct()
        ),
        children=list(Person.objects.filter(parent_links__parent=person).distinct()),
        siblings=list(siblings.exclude(pk=person.pk).distinct()),
    )


@dataclass(frozen=True, kw_only=True)
class PersonListEntry:
    person: Person
    name: str
    initials: str
    lifespan: str


@dataclass(frozen=True, kw_only=True)
class PersonList:
    entries: list[PersonListEntry]
    total: int


def person_list(*, search: str) -> PersonList:
    """
    The people of the sidebar (#10) whose names match "search", sorted by family name, each with the name they
    went by, their initials and their Lebensdaten - plus how many people there are at all. Filtered and sorted
    in Python rather than in the query: SQLite compares umlauts neither case-insensitively nor in German
    order, and one family is few enough rows to read whole.
    """
    persons = _with_life_facts()
    found = [
        person
        for person in persons
        if matches(search=search, names=(person.given_names, person.surname, person.call_name))
    ]
    found.sort(key=lambda person: sort_key(given_names=person.given_names, surname=person.surname))

    return PersonList(entries=[_entry(person=person) for person in found], total=len(persons))


def person_entries(*, person_ids: Iterable[int]) -> dict[int, PersonListEntry]:
    """
    The name, initials and Lebensdaten of each of "person_ids", by id - what a card in the tree (#12) shows.
    """
    return {person.pk: _entry(person=person) for person in _with_life_facts().filter(pk__in=person_ids)}


@dataclass(frozen=True, kw_only=True)
class FactEntry:
    fact: Fact
    # What the fact is - "Geboren", "Beruf", or a custom fact's own label - and what it says.
    label: str
    text: str
    # "Wahrscheinlich" or "Überliefert", None for a fact marked documented.
    reliability: str | None
    citations: list[Citation]
    # Marked documented without a citation - "unbelegt", see docs/patterns/evidence.md.
    undocumented: bool


@dataclass(frozen=True, kw_only=True)
class RelativeGroup:
    title: str
    entries: list[PersonListEntry]


@dataclass(frozen=True, kw_only=True)
class PersonCard:
    entry: PersonListEntry
    # How the person is related to the home person, None while nobody is chosen or nothing connects them.
    relationship: str | None
    facts: list[FactEntry]
    relatives: list[RelativeGroup]
    relative_count: int
    # Whether a death fact is recorded, so the form for name and status (#30) does not ask for the year again.
    death_recorded: bool


def person_card(*, pk: int) -> PersonCard | None:
    """
    The person card (#12, #13): the head with name, Lebensdaten and how the person is related to the home person,
    every fact with its reliability and its Belege, and everyone directly related - or None for a person who is
    not there.
    """
    person = _with_life_facts().filter(pk=pk).first()
    if person is None:
        return None

    found = relatives(person=person)
    groups = (
        ("Eltern", found.parents),
        ("Partner", found.partners),
        ("Kinder", found.children),
        ("Geschwister", found.siblings),
    )
    entries = person_entries(person_ids=[relative.pk for _, members in groups for relative in members])
    home = home_person()

    return PersonCard(
        entry=_entry(person=person),
        relationship=(relationship_name(family=family_graph(), home_id=home.pk, person_id=person.pk) if home else None),
        facts=[_fact_entry(fact=fact) for fact in facts(person=person)],
        relatives=[
            RelativeGroup(title=title, entries=[entries[relative.pk] for relative in members])
            for title, members in groups
            if members
        ],
        relative_count=sum(len(members) for _, members in groups),
        death_recorded=any(fact.kind == Fact.Kind.DEATH for fact in person.life_facts),
    )


def _with_life_facts() -> QuerySet[Person]:
    return Person.objects.prefetch_related(
        Prefetch(
            "facts",
            queryset=Fact.objects.filter(kind__in=(Fact.Kind.BIRTH, Fact.Kind.DEATH)),
            to_attr="life_facts",
        )
    )


def _entry(*, person: Person) -> PersonListEntry:
    # The facts come in the model's date order, so the first of a kind is the earliest one recorded.
    births = [fact.date for fact in person.life_facts if fact.kind == Fact.Kind.BIRTH]
    deaths = [fact.date for fact in person.life_facts if fact.kind == Fact.Kind.DEATH]
    return PersonListEntry(
        person=person,
        name=display_name(given_names=person.given_names, surname=person.surname, call_name=person.call_name),
        initials=initials(given_names=person.given_names, surname=person.surname),
        lifespan=lifespan(
            birth=next(iter(births), None),
            death=next(iter(deaths), None),
            deceased=person.living_status == Person.LivingStatus.DECEASED,
        ),
    )


def _fact_entry(*, fact: Fact) -> FactEntry:
    date = fact.date
    return FactEntry(
        fact=fact,
        label=fact.label or fact.get_kind_display(),
        # Only a custom fact may carry both, e.g. a first communion with its place.
        text=", ".join(part for part in (fact.value, date_text(date=date) if date else "") if part),
        reliability=(
            None if fact.reliability == Fact.Reliability.DOCUMENTED else fact.get_reliability_display().capitalize()
        ),
        citations=list(fact.citations.all()),
        undocumented=fact.undocumented,
    )
