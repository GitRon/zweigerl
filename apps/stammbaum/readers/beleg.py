from django.db.models import Exists, F, OuterRef, Q, QuerySet

from apps.stammbaum.models import Angabe, Person, Quelle, Zitat


def angaben(*, person: Person) -> QuerySet[Angabe]:
    """
    A person's Angaben in date order, those without a date last, each annotated with "unbelegt" - marked
    "belegt" without a Zitat, see docs/patterns/belege.md. The Angaben of their partnerships are not among
    them; those belong to the couple.
    """
    return (
        Angabe.objects.filter(person=person)
        .annotate(
            unbelegt=Q(verlaesslichkeit=Angabe.Verlaesslichkeit.BELEGT)
            & ~Exists(Zitat.objects.filter(angabe=OuterRef("pk")))
        )
        .prefetch_related("zitate__quelle")
        .order_by(F("sortierdatum").asc(nulls_last=True), "art", "pk")
    )


def quellen(*, person: Person) -> QuerySet[Quelle]:
    """
    The sources of a person: those filed with them, and those any of their Angaben cites. What #14 offers to
    cite and #15 lists on the card.
    """
    return Quelle.objects.filter(Q(personen=person) | Q(zitate__angabe__person=person)).distinct()
