from dataclasses import dataclass

from django.db.models import Exists, OuterRef, Q, QuerySet

from apps.family_tree.domain.names import display_name
from apps.family_tree.models import Citation, Fact, Person, Source, SourceFile


def facts(*, person: Person) -> QuerySet[Fact]:
    """
    A person's facts and those of their partnerships - a marriage belongs to the couple, but it is shown and
    edited on either partner's card (#14) - in date order, those without a date last (the model's ordering),
    each annotated with "undocumented": marked documented without a citation, "unbelegt", see
    docs/patterns/evidence.md.
    """
    return (
        Fact.objects.filter(Q(person=person) | Q(partnership__person_a=person) | Q(partnership__person_b=person))
        .select_related("partnership__person_a", "partnership__person_b", "gedcom_import")
        .annotate(
            undocumented=Q(reliability=Fact.Reliability.DOCUMENTED)
            & ~Exists(Citation.objects.filter(fact=OuterRef("pk")))
        )
        .prefetch_related("citations__source")
    )


def sources(*, person: Person) -> QuerySet[Source]:
    """
    The sources of a person: those filed with them, those any of their facts cites, and those cited by the
    facts of their partnerships - a marriage certificate is the couple's. What #14 offers to cite and #15
    lists on the card.
    """
    return Source.objects.filter(
        Q(people=person)
        | Q(citations__fact__person=person)
        | Q(citations__fact__partnership__person_a=person)
        | Q(citations__fact__partnership__person_b=person)
    ).distinct()


@dataclass(frozen=True, kw_only=True)
class SourceDeletion:
    source: Source
    file_count: int
    # The facts citing it, as "Geboren · Lena Huber"; while there is one, the source stays (#72).
    citing: list[str]


def source_deletion(*, source_id: int) -> SourceDeletion | None:
    """
    What deleting a source would take with it, for the question before "Quelle löschen" (#72) - or None for a
    source that is not there.
    """
    source = Source.objects.filter(pk=source_id).first()
    if source is None:
        return None

    citing = Fact.objects.filter(citations__source=source).select_related(
        "person", "partnership__person_a", "partnership__person_b"
    )
    return SourceDeletion(
        source=source,
        file_count=source.files.count(),
        citing=[f"{fact.label or fact.get_kind_display()} · {_owner_name(fact=fact)}" for fact in citing],
    )


def _owner_name(*, fact: Fact) -> str:
    owners = [fact.person] if fact.person else [fact.partnership.person_a, fact.partnership.person_b]
    return " und ".join(
        display_name(given_names=owner.given_names, surname=owner.surname, call_name=owner.call_name)
        for owner in owners
    )


@dataclass(frozen=True, kw_only=True)
class SourceFileDeletion:
    source_file: SourceFile
    # Its place among the files of the source, as the card counts them: "Datei 2".
    number: int


def source_file_deletion(*, source_id: int, file_id: int) -> SourceFileDeletion | None:
    """
    One scan or PDF of a source, for the question before "Datei entfernen" (#72) - or None for a file that is
    not the source's or no longer there.
    """
    source_file = SourceFile.objects.filter(pk=file_id, source_id=source_id).select_related("source").first()
    if source_file is None:
        return None

    return SourceFileDeletion(
        source_file=source_file,
        number=SourceFile.objects.filter(source_id=source_id, pk__lte=file_id).count(),
    )
