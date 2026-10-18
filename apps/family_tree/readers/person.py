from dataclasses import dataclass

from django.db.models import Prefetch, Q

from apps.family_tree.domain.dates import lifespan
from apps.family_tree.domain.names import display_name, initials, matches, sort_key
from apps.family_tree.models import Fact, Person, SiblingPair


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
    persons = Person.objects.prefetch_related(
        Prefetch(
            "facts",
            queryset=Fact.objects.filter(kind__in=(Fact.Kind.BIRTH, Fact.Kind.DEATH)),
            to_attr="life_facts",
        )
    )
    found = [
        person
        for person in persons
        if matches(search=search, names=(person.given_names, person.surname, person.call_name))
    ]
    found.sort(key=lambda person: sort_key(given_names=person.given_names, surname=person.surname))

    return PersonList(entries=[_entry(person=person) for person in found], total=len(persons))


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
