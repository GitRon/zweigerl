from collections.abc import Iterable
from dataclasses import dataclass

from django.db.models import Prefetch, Q, QuerySet

from apps.family_tree.domain.dates import date_text, lifespan
from apps.family_tree.domain.names import display_name, initials, matches, sort_key
from apps.family_tree.domain.relationship import relationship_name
from apps.family_tree.models import Citation, Fact, Partnership, Person, SiblingPair, Source
from apps.family_tree.models.fact import COUPLE_KINDS, CUSTOM, VALUE_KINDS
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
    # The name of the other partner for a fact of the couple, a marriage (#14); None for the person's own.
    partner: str | None = None


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
class PersonCard:
    entry: PersonListEntry
    # How the person is related to the home person, None while nobody is chosen or nothing connects them.
    relationship: str | None
    facts: list[FactEntry]
    relatives: list[RelativeGroup]
    relative_count: int
    sources_tab: SourcesTab
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
        facts=[_fact_entry(fact=fact, person=person) for fact in facts(person=person)],
        relatives=[
            RelativeGroup(title=title, entries=[entries[relative.pk] for relative in members])
            for title, members in groups
            if members
        ],
        relative_count=sum(len(members) for _, members in groups),
        sources_tab=_sources_tab(person=person),
        death_recorded=any(fact.kind == Fact.Kind.DEATH for fact in person.life_facts),
    )


def fact_entry(*, person_id: int, fact_id: int) -> FactEntry | None:
    """
    One fact of the person or of one of their partnerships as their card shows it, for asking before it is
    removed (#14) - or None for a fact that is not theirs or no longer there.
    """
    person = Person.objects.filter(pk=person_id).first()
    fact = facts(person=person).filter(pk=fact_id).first() if person else None
    return _fact_entry(fact=fact, person=person) if fact else None


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


@dataclass(frozen=True, kw_only=True)
class KindChoice:
    value: str
    label: str
    # Which fields the form shows for it: "date", "value", "custom" - label, value and date - or "couple", the
    # partner and the date.
    fields: str


@dataclass(frozen=True, kw_only=True)
class CitationChoice:
    source: Source
    cited: bool
    # The place in the source, "Stelle"; empty while the source is not cited.
    page: str


@dataclass(frozen=True, kw_only=True)
class FactForm:
    person: Person
    # None for a new fact.
    fact: Fact | None
    kind: str
    fields: str
    label: str
    value: str
    # The date as German text, the way the card writes it and the form reads it back.
    date: str
    partner_id: int | None
    reliability: str
    # Marriage and divorce only for somebody with a partner, since they go on the partnership.
    kinds: list[KindChoice]
    partners: list[PersonListEntry]
    reliabilities: list[tuple[str, str]]
    # Every source of the person, each saying whether the fact cites it and where.
    citations: list[CitationChoice]

    @property
    def key(self) -> str:
        # What the form's id and its signal are named after: the fact it edits, or "new".
        return str(self.fact.pk) if self.fact else "new"


def fact_form(*, person_id: int, fact_id: int | None = None) -> FactForm | None:
    """
    What the form for a fact on the person card (#14) shows: the fact "fact_id" as it is, or a new birth date
    without one - or None for a person who is not there, or a fact that is not theirs or theirs no more.
    """
    person = Person.objects.filter(pk=person_id).first()
    if person is None:
        return None
    fact = facts(person=person).filter(pk=fact_id).first() if fact_id is not None else None
    if fact_id is not None and fact is None:
        return None

    shown = fact or Fact(kind=Fact.Kind.BIRTH)
    partners = relatives(person=person).partners
    entries = person_entries(person_ids=[partner.pk for partner in partners])
    cited = {citation.source_id: citation.page for citation in fact.citations.all()} if fact else {}
    date = shown.date

    return FactForm(
        person=person,
        fact=fact,
        kind=shown.kind,
        fields=_fields(kind=shown.kind),
        label=shown.label,
        value=shown.value,
        date=date_text(date=date) if date else "",
        partner_id=_partner(partnership=shown.partnership, person=person).pk if shown.partnership else None,
        reliability=shown.reliability,
        kinds=[
            KindChoice(value=value, label=label, fields=_fields(kind=value))
            for value, label in Fact.Kind.choices
            if partners or value not in COUPLE_KINDS
        ],
        partners=[entries[partner.pk] for partner in partners],
        reliabilities=list(Fact.Reliability.choices),
        citations=[
            CitationChoice(source=source, cited=source.pk in cited, page=cited.get(source.pk, ""))
            for source in sources(person=person)
        ],
    )


def _fields(*, kind: str) -> str:
    if kind in COUPLE_KINDS:
        return "couple"
    if kind in VALUE_KINDS:
        return "value"
    return "custom" if kind == CUSTOM else "date"


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


def _fact_entry(*, fact: Fact, person: Person) -> FactEntry:
    date = fact.date
    partner = _partner(partnership=fact.partnership, person=person) if fact.partnership else None
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
        partner=(
            display_name(given_names=partner.given_names, surname=partner.surname, call_name=partner.call_name)
            if partner
            else None
        ),
    )


def _partner(*, partnership: Partnership, person: Person) -> Person:
    return partnership.person_b if partnership.person_a_id == person.pk else partnership.person_a
