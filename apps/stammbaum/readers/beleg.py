from django.db.models import Exists, OuterRef, Q, QuerySet

from apps.stammbaum.models import Angabe, Person, Quelle, Zitat


def angaben(*, person: Person) -> QuerySet[Angabe]:
    """
    A person's Angaben in date order, those without a date last (the model's ordering), each annotated
    with "unbelegt" - marked "belegt" without a Zitat, see docs/patterns/belege.md. The Angaben of their
    partnerships are not among them; those belong to the couple.
    """
    return (
        Angabe.objects.filter(person=person)
        .annotate(
            unbelegt=Q(verlaesslichkeit=Angabe.Verlaesslichkeit.BELEGT)
            & ~Exists(Zitat.objects.filter(angabe=OuterRef("pk")))
        )
        .prefetch_related("zitate__quelle")
    )


def quellen(*, person: Person) -> QuerySet[Quelle]:
    """
    The sources of a person: those filed with them, those any of their Angaben cites, and those cited by the
    Angaben of their partnerships - a marriage certificate is the couple's. What #14 offers to cite and #15
    lists on the card.
    """
    return Quelle.objects.filter(
        Q(personen=person)
        | Q(zitate__angabe__person=person)
        | Q(zitate__angabe__partnerschaft__person_a=person)
        | Q(zitate__angabe__partnerschaft__person_b=person)
    ).distinct()
