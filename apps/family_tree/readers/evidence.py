from django.db.models import Exists, OuterRef, Q, QuerySet

from apps.family_tree.models import Citation, Fact, Person, Source


def facts(*, person: Person) -> QuerySet[Fact]:
    """
    A person's facts and those of their partnerships - a marriage belongs to the couple, but it is shown and
    edited on either partner's card (#14) - in date order, those without a date last (the model's ordering),
    each annotated with "undocumented": marked documented without a citation, "unbelegt", see
    docs/patterns/evidence.md.
    """
    return (
        Fact.objects.filter(Q(person=person) | Q(partnership__person_a=person) | Q(partnership__person_b=person))
        .select_related("partnership__person_a", "partnership__person_b")
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
