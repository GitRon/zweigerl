from ambient_toolbox.mixins.validation import ValidateConstraintsOnSaveMixin
from django.db import models
from django.db.models.functions import Greatest, Least

from apps.stammbaum.models.gedcom import GedcomRohMixin


class Partnerschaft(ValidateConstraintsOnSaveMixin, GedcomRohMixin):
    """
    Two people as a couple - GEDCOM's FAM with HUSB and WIFE, MARR and DIV. The through model of
    Person.partner. Which of the two is "person_a" means nothing; a pair is stored once either way round.
    """

    class Art(models.TextChoices):
        EHE = "ehe", "Ehe"
        LEBENSGEMEINSCHAFT = "lebensgemeinschaft", "Lebensgemeinschaft"
        UNBEKANNT = "unbekannt", "unbekannt"

    person_a = models.ForeignKey(
        "stammbaum.Person", verbose_name="Person", on_delete=models.CASCADE, related_name="partnerschaften_als_a"
    )
    person_b = models.ForeignKey(
        "stammbaum.Person", verbose_name="Partner", on_delete=models.CASCADE, related_name="partnerschaften_als_b"
    )
    art = models.CharField("Art", max_length=20, choices=Art, default=Art.UNBEKANNT)
    # GEDCOM DATE syntax ("1985", "ABT 1931", "BET 1950 AND 1952") until the structured uncertain date of
    # docs/patterns/belege.md arrives with #8, which replaces both.
    beginn = models.CharField(
        "Beginn", max_length=50, blank=True, help_text="GEDCOM-Datum, z. B. „1985“ oder „ABT 1931“"
    )
    ende = models.CharField("Ende", max_length=50, blank=True, help_text="GEDCOM-Datum, z. B. „2009“")

    class Meta:
        verbose_name = "Partnerschaft"
        verbose_name_plural = "Partnerschaften"
        constraints = (
            models.CheckConstraint(
                condition=~models.Q(person_a=models.F("person_b")),
                name="partnerschaft_nicht_selbst",
                violation_error_message="Niemand ist sein eigener Partner.",
            ),
            # On the pair rather than on the two columns, so B & A is refused once A & B exists.
            models.UniqueConstraint(
                Least("person_a", "person_b"),
                Greatest("person_a", "person_b"),
                name="partnerschaft_einmal_pro_paar",
                violation_error_message="Diese beiden sind schon ein Paar.",
            ),
            models.CheckConstraint(
                condition=models.Q(art__in=("ehe", "lebensgemeinschaft", "unbekannt")),
                name="partnerschaft_art_gueltig",
                violation_error_message="Eine Partnerschaft ist eine Ehe, eine Lebensgemeinschaft oder unbekannt.",
            ),
        )

    def __str__(self) -> str:
        return f"{self.person_a} & {self.person_b}"

    def enthaelt(self, *, person_id: int) -> bool:
        return person_id in (self.person_a_id, self.person_b_id)
