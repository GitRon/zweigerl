from ambient_toolbox.mixins.validation import ValidateConstraintsOnSaveMixin
from django.db import models

from apps.family_tree.models.gedcom import GedcomRawMixin


class Person(ValidateConstraintsOnSaveMixin, GedcomRawMixin):
    """
    One person in the tree - GEDCOM's INDI. Dates and places are Angaben with their Beleg (#8), not fields here.
    """

    class Sex(models.TextChoices):
        # GEDCOM SEX: M, F, X, U
        MALE = "M", "männlich"
        FEMALE = "F", "weiblich"
        DIVERSE = "X", "divers"
        UNKNOWN = "U", "unbekannt"

    class LivingStatus(models.TextChoices):
        # GEDCOM has no field for it: "deceased" is a DEAT record, "living" its absence on someone born
        # recently enough. "unknown" is the default so an import of someone born in 1820 without a death
        # record does not land as alive.
        LIVING = "living", "lebend"
        DECEASED = "deceased", "verstorben"
        UNKNOWN = "unknown", "unbekannt"

    # GEDCOM NAME /SURN/ with GIVN and NICK. Every one may be empty: GEDCOM allows a person without a name,
    # and "the unknown first wife" is a person in the tree.
    given_names = models.CharField("Vornamen", max_length=200, blank=True)
    surname = models.CharField("Familienname", max_length=200, blank=True)
    call_name = models.CharField("Rufname", max_length=100, blank=True)
    sex = models.CharField("Geschlecht", max_length=1, choices=Sex, default=Sex.UNKNOWN)
    living_status = models.CharField("Lebensstatus", max_length=10, choices=LivingStatus, default=LivingStatus.UNKNOWN)
    # Symmetrical in meaning but stored once per pair, so this only reaches the partners stored as
    # "person_b" - readers.person.relatives looks at both sides. No reverse accessor: it would be the other
    # half of the same pairs under a second name.
    partners = models.ManyToManyField(
        "self",
        through="family_tree.Partnership",
        through_fields=("person_a", "person_b"),
        symmetrical=False,
        blank=True,
        related_name="+",
    )

    class Meta:
        verbose_name = "Person"
        verbose_name_plural = "Personen"
        ordering = ("surname", "given_names", "pk")
        constraints = (
            # The values of the choices above, written out: a migration freezes them anyway, and a nested
            # Meta cannot see the enclosing class.
            models.CheckConstraint(
                condition=models.Q(sex__in=("M", "F", "X", "U")),
                name="person_sex_valid",
                violation_error_message="Das Geschlecht ist männlich, weiblich, divers oder unbekannt.",
            ),
            models.CheckConstraint(
                condition=models.Q(living_status__in=("living", "deceased", "unknown")),
                name="person_living_status_valid",
                violation_error_message="Der Lebensstatus ist lebend, verstorben oder unbekannt.",
            ),
        )

    def __str__(self) -> str:
        return " ".join(part for part in (self.given_names, self.surname) if part) or "Ohne Namen"
