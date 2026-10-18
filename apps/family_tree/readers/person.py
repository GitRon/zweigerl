from collections.abc import Iterable
from dataclasses import dataclass

from django.db.models import F, Prefetch, Q, QuerySet

from apps.family_tree.domain.dates import DateParts, date_text, lifespan, to_parts
from apps.family_tree.domain.names import display_name, initials, matches, sort_key
from apps.family_tree.domain.relationship import relationship_name
from apps.family_tree.models import Citation, Fact, Person, PhotoPerson, SiblingPair, Source
from apps.family_tree.readers.evidence import facts, sources
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
    # The portrait the picture frame shows (#16), "" while there is none, and what it shows.
    portrait_url: str = ""
    portrait_alt: str = ""


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
class SourcesTab:
    person: Person
    # Filed with the person or cited by their facts, each with its files (#15).
    sources: list[Source]
    # What the form for a new source offers, as (value, label).
    kinds: list[tuple[str, str]]


@dataclass(frozen=True, kw_only=True)
class PhotoEntry:
    link: PhotoPerson
    url: str
    alt: str
    # When it was taken, as the card says it - "" while nobody knows - and as the form asks for it.
    date_text: str
    date_parts: DateParts


@dataclass(frozen=True, kw_only=True)
class PhotosTab:
    person: Person
    # The person's photos, the oldest first and those without a date last (#16).
    photos: list[PhotoEntry]


@dataclass(frozen=True, kw_only=True)
class PersonCard:
    entry: PersonListEntry
    # How the person is related to the home person, None while nobody is chosen or nothing connects them.
    relationship: str | None
    facts: list[FactEntry]
    relatives: list[RelativeGroup]
    relative_count: int
    sources_tab: SourcesTab
    photos_tab: PhotosTab
    # Whether a death fact is recorded, so the form for name and status (#30) does not ask for the year again.
    death_recorded: bool


def person_card(*, pk: int) -> PersonCard | None:
    """
    The person card (#12, #13): the head with name, Lebensdaten and how the person is related to the home person,
    every fact with its reliability and its Belege, everyone directly related and the sources with their files -
    or None for a person who is not there.
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
        sources_tab=_sources_tab(person=person),
        photos_tab=_photos_tab(person=person),
        death_recorded=any(fact.kind == Fact.Kind.DEATH for fact in person.life_facts),
    )


def sources_tab(*, pk: int) -> SourcesTab | None:
    """
    The Quellen tab of the person card (#15) on its own, for patching it after a source was added - or None for
    a person who is not there.
    """
    person = Person.objects.filter(pk=pk).first()
    return _sources_tab(person=person) if person else None


def _sources_tab(*, person: Person) -> SourcesTab:
    return SourcesTab(
        person=person,
        sources=list(sources(person=person).prefetch_related("files")),
        kinds=list(Source.Kind.choices),
    )


def photos_tab(*, pk: int) -> PhotosTab | None:
    """
    The Fotos tab of the person card (#16) on its own, for patching it after a photo was added or changed - or
    None for a person who is not there.
    """
    person = Person.objects.filter(pk=pk).first()
    return _photos_tab(person=person) if person else None


def _photos_tab(*, person: Person) -> PhotosTab:
    links = (
        PhotoPerson.objects.filter(person=person)
        .select_related("photo")
        .order_by(F("photo__sort_date").asc(nulls_last=True), "photo__pk")
    )
    return PhotosTab(
        person=person,
        photos=[
            PhotoEntry(
                link=link,
                url=link.photo.file.url,
                alt=_alt(description=link.photo.description),
                date_text=date_text(date=link.photo.date) if link.photo.date else "",
                date_parts=to_parts(date=link.photo.date),
            )
            for link in links
        ],
    )


def _with_life_facts() -> QuerySet[Person]:
    return Person.objects.prefetch_related(
        Prefetch(
            "facts",
            queryset=Fact.objects.filter(kind__in=(Fact.Kind.BIRTH, Fact.Kind.DEATH)),
            to_attr="life_facts",
        ),
        Prefetch(
            "photo_links",
            queryset=PhotoPerson.objects.filter(is_portrait=True).select_related("photo"),
            to_attr="portraits",
        ),
    )


def _entry(*, person: Person) -> PersonListEntry:
    # The facts come in the model's date order, so the first of a kind is the earliest one recorded.
    births = [fact.date for fact in person.life_facts if fact.kind == Fact.Kind.BIRTH]
    deaths = [fact.date for fact in person.life_facts if fact.kind == Fact.Kind.DEATH]
    portrait = next(iter(person.portraits), None)
    return PersonListEntry(
        person=person,
        name=display_name(given_names=person.given_names, surname=person.surname, call_name=person.call_name),
        initials=initials(given_names=person.given_names, surname=person.surname),
        lifespan=lifespan(
            birth=next(iter(births), None),
            death=next(iter(deaths), None),
            deceased=person.living_status == Person.LivingStatus.DECEASED,
        ),
        portrait_url=portrait.photo.file.url if portrait else "",
        portrait_alt=_alt(description=portrait.photo.description) if portrait else "",
    )


def _alt(*, description: str) -> str:
    # The frame announces only the photo, so its alt describes the picture rather than repeating the name.
    return description or "Foto ohne Beschreibung"


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
