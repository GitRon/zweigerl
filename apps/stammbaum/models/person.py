from django.db import models

from apps.stammbaum.models.gedcom import GedcomRohMixin


class Person(GedcomRohMixin):
    """
    One person in the tree - GEDCOM's INDI. Dates and places are Angaben with their Beleg (#8), not fields here.
    """

    class Geschlecht(models.TextChoices):
        # GEDCOM SEX: M, F, X, U
        MAENNLICH = "M", "männlich"
        WEIBLICH = "F", "weiblich"
        DIVERS = "X", "divers"
        UNBEKANNT = "U", "unbekannt"

    class Lebensstatus(models.TextChoices):
        # GEDCOM has no field for it: "verstorben" is a DEAT record, "lebend" its absence on someone born
        # recently enough. "unbekannt" is the default so an import of someone born in 1820 without a death
        # record does not land as alive.
        LEBEND = "lebend", "lebend"
        VERSTORBEN = "verstorben", "verstorben"
        UNBEKANNT = "unbekannt", "unbekannt"

    # GEDCOM NAME /SURN/ with GIVN and NICK
    vornamen = models.CharField("Vornamen", max_length=200, blank=True)
    familienname = models.CharField("Familienname", max_length=200, blank=True)
    rufname = models.CharField("Rufname", max_length=100, blank=True)
    geschlecht = models.CharField("Geschlecht", max_length=1, choices=Geschlecht, default=Geschlecht.UNBEKANNT)
    lebensstatus = models.CharField("Lebensstatus", max_length=10, choices=Lebensstatus, default=Lebensstatus.UNBEKANNT)
    # Symmetrical in meaning but stored once per pair, so this only reaches the partners stored as
    # "person_b" - readers.person.verwandte looks at both sides. No reverse accessor: it would be the other
    # half of the same pairs under a second name.
    partner = models.ManyToManyField(
        "self",
        through="stammbaum.Partnerschaft",
        through_fields=("person_a", "person_b"),
        symmetrical=False,
        blank=True,
        related_name="+",
    )

    class Meta:
        verbose_name = "Person"
        verbose_name_plural = "Personen"
        ordering = ("familienname", "vornamen", "pk")

    def __str__(self) -> str:
        return " ".join(part for part in (self.vornamen, self.familienname) if part) or "Ohne Namen"
