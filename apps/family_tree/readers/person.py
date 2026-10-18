from collections.abc import Iterable
from dataclasses import dataclass

from django.db.models import F, Prefetch, Q, QuerySet

from apps.family_tree.domain.dates import date_text, lifespan
from apps.family_tree.domain.names import display_name, initials, matches, sort_key
from apps.family_tree.domain.relationship import connected_people, relationship_name
from apps.family_tree.models import Citation, Fact, Partnership, Person, PhotoPerson, SiblingPair, Source
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
    # The name of the other partner for a fact of the couple, a marriage (#14); None for the person's own.
    partner: str | None = None


@dataclass(frozen=True, kw_only=True)
class RelativeEntry:
    entry: PersonListEntry
    # Whether a link of its own joins the two, which "Verbindung lösen" removes (#19). A sibling through a shared
    # parent has none: that link is the parent's.
    unlinkable: bool


@dataclass(frozen=True, kw_only=True)
class RelativeGroup:
    title: str
    # "parent", "partner", "child" or "sibling": what the relatives of the group are to the person.
    relation: str
    entries: list[RelativeEntry]


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
    # When it was taken, as the card writes it and the form reads it back - "" while nobody knows.
    date: str


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

    groups = relative_groups(person=person)
    home = home_person()

    return PersonCard(
        entry=_entry(person=person),
        relationship=(relationship_name(family=family_graph(), home_id=home.pk, person_id=person.pk) if home else None),
        facts=[_fact_entry(fact=fact, person=person) for fact in facts(person=person)],
        relatives=groups,
        relative_count=sum(len(group.entries) for group in groups),
        sources_tab=_sources_tab(person=person),
        photos_tab=_photos_tab(person=person),
        death_recorded=any(fact.kind == Fact.Kind.DEATH for fact in person.life_facts),
    )


def relative_groups(*, person: Person) -> list[RelativeGroup]:
    """
    Everyone directly related to "person", in the groups the card shows them in - parents, partners, children,
    siblings - leaving out the empty ones. Each says whether a link of its own joins them to the person.
    """
    found = relatives(person=person)
    explicit_siblings = {
        *SiblingPair.objects.filter(person_a=person).values_list("person_b", flat=True),
        *SiblingPair.objects.filter(person_b=person).values_list("person_a", flat=True),
    }
    groups = (
        ("Eltern", "parent", found.parents),
        ("Partner", "partner", found.partners),
        ("Kinder", "child", found.children),
        ("Geschwister", "sibling", found.siblings),
    )
    entries = person_entries(person_ids=[relative.pk for _, _, members in groups for relative in members])
    return [
        RelativeGroup(
            title=title,
            relation=relation,
            entries=[
                RelativeEntry(
                    entry=entries[relative.pk], unlinkable=relation != "sibling" or relative.pk in explicit_siblings
                )
                for relative in members
            ],
        )
        for title, relation, members in groups
        if members
    ]


@dataclass(frozen=True, kw_only=True)
class DeletionPreview:
    entry: PersonListEntry
    # The home person cannot be deleted: another one is chosen first.
    home: bool
    # What vanishes with the person: their facts and those of their partnerships, and the citations of them.
    fact_count: int
    citation_count: int
    # What stays: the sources on their card, cited by their facts or not - decided in #19.
    source_count: int
    # Every link that goes with them, by what the relatives were to them.
    relatives: list[RelativeGroup]
    # Who is connected to the home person now and would hang loose afterwards.
    cut_off: list[PersonListEntry]


def deletion_preview(*, pk: int) -> DeletionPreview | None:
    """
    What deleting the person "pk" would take with it and whom it would cut off from the home person (#19), for
    the dialog that asks first - or None for a person who is not there.
    """
    person = _with_life_facts().filter(pk=pk).first()
    if person is None:
        return None

    vanishing_facts = Fact.objects.filter(
        Q(person=person) | Q(partnership__person_a=person) | Q(partnership__person_b=person)
    )
    home = home_person()
    return DeletionPreview(
        entry=_entry(person=person),
        home=home is not None and home.pk == pk,
        fact_count=vanishing_facts.count(),
        citation_count=Citation.objects.filter(fact__in=vanishing_facts).count(),
        source_count=sources(person=person).count(),
        relatives=relative_groups(person=person),
        cut_off=_cut_off(pk=pk, home=home),
    )


def _cut_off(*, pk: int, home: Person | None) -> list[PersonListEntry]:
    if home is not None and home.pk == pk:
        return []
    before = _connected(anchor_id=_anchor_id(home=home), without_id=None)
    after = _connected(anchor_id=_anchor_id(home=home, without_id=pk), without_id=pk)
    return _sorted_entries(person_ids=before - after - {pk})


RELATION_NAMES = {"parent": "Elternteil", "partner": "Partner", "child": "Kind", "sibling": "Geschwister"}


@dataclass(frozen=True, kw_only=True)
class LinkPreview:
    person: PersonListEntry
    relative: PersonListEntry
    relation: str
    # What the relative is to the person: "Elternteil", "Partner", "Kind" or "Geschwister".
    relation_name: str
    # The facts of a couple - when they married, when they divorced - which go with their partnership.
    couple_fact_count: int


def link_preview(*, pk: int, relation: str, relative_pk: int) -> LinkPreview | None:
    """
    The one link "Verbindung lösen" would remove (#19): "relative_pk" as the parent, partner, child or explicit
    sibling of "pk" - or None when no such link joins the two.
    """
    person_q = {
        "parent": Q(child_links__child=pk),
        "partner": Q(partnerships_as_a__person_b=pk) | Q(partnerships_as_b__person_a=pk),
        "child": Q(parent_links__parent=pk),
        "sibling": Q(sibling_pairs_as_a__person_b=pk) | Q(sibling_pairs_as_b__person_a=pk),
    }.get(relation)
    if person_q is None or not Person.objects.filter(person_q, pk=relative_pk).exists():
        return None

    entries = person_entries(person_ids=[pk, relative_pk])
    couple_facts = Fact.objects.filter(
        Q(partnership__person_a=pk, partnership__person_b=relative_pk)
        | Q(partnership__person_a=relative_pk, partnership__person_b=pk)
    )
    return LinkPreview(
        person=entries[pk],
        relative=entries[relative_pk],
        relation=relation,
        relation_name=RELATION_NAMES[relation],
        couple_fact_count=couple_facts.count() if relation == "partner" else 0,
    )


def loose_people() -> list[PersonListEntry]:
    """
    The "Lose Zweigerl" of the sidebar (#19): everyone with no connection to the home person, or - while nobody is
    chosen - to the person entered first, whom the tree is laid out around then. Nothing ever deletes them on its
    own; they wait to be connected again or deleted.
    """
    connected = _connected(anchor_id=_anchor_id(home=home_person()), without_id=None)
    return _sorted_entries(person_ids=set(Person.objects.exclude(pk__in=connected).values_list("pk", flat=True)))


def _anchor_id(*, home: Person | None, without_id: int | None = None) -> int | None:
    # The person the tree is laid out around, as "readers.tree.tree_layout" chooses them.
    if home is not None:
        return home.pk
    return Person.objects.exclude(pk=without_id).order_by("pk").values_list("pk", flat=True).first()


def _connected(*, anchor_id: int | None, without_id: int | None) -> frozenset[int]:
    if anchor_id is None:
        return frozenset()
    return connected_people(family=family_graph(without_id=without_id), start_id=anchor_id)


def _sorted_entries(*, person_ids: set[int]) -> list[PersonListEntry]:
    entries = list(person_entries(person_ids=person_ids).values())
    entries.sort(key=lambda entry: sort_key(given_names=entry.person.given_names, surname=entry.person.surname))
    return entries


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
                date=date_text(date=link.photo.date) if link.photo.date else "",
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
