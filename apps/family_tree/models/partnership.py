from ambient_toolbox.mixins.validation import ValidateConstraintsOnSaveMixin
from django.db import models
from django.db.models.functions import Greatest, Least

from apps.family_tree.models.gedcom import GedcomRawMixin


class Partnership(ValidateConstraintsOnSaveMixin, GedcomRawMixin):
    """
    Two people as a couple - GEDCOM's FAM with HUSB and WIFE. The through model of Person.partners. When they
    married or divorced are facts on it (MARR, DIV), with their citations. Which of the two is "person_a"
    means nothing; a pair is stored once either way round.
    """

    class Kind(models.TextChoices):
        MARRIAGE = "marriage", "Ehe"
        COHABITATION = "cohabitation", "Lebensgemeinschaft"
        UNKNOWN = "unknown", "unbekannt"

    person_a = models.ForeignKey(
        "family_tree.Person", verbose_name="Person", on_delete=models.CASCADE, related_name="partnerships_as_a"
    )
    person_b = models.ForeignKey(
        "family_tree.Person", verbose_name="Partner", on_delete=models.CASCADE, related_name="partnerships_as_b"
    )
    kind = models.CharField("Art", max_length=20, choices=Kind, default=Kind.UNKNOWN)

    class Meta:
        verbose_name = "Partnerschaft"
        verbose_name_plural = "Partnerschaften"
        constraints = (
            models.CheckConstraint(
                condition=~models.Q(person_a=models.F("person_b")),
                name="partnership_not_self",
                violation_error_message="Niemand ist sein eigener Partner.",
            ),
            # On the pair rather than on the two columns, so B & A is refused once A & B exists.
            models.UniqueConstraint(
                Least("person_a", "person_b"),
                Greatest("person_a", "person_b"),
                name="partnership_once_per_pair",
                violation_error_message="Diese beiden sind schon ein Paar.",
            ),
            models.CheckConstraint(
                condition=models.Q(kind__in=("marriage", "cohabitation", "unknown")),
                name="partnership_kind_valid",
                violation_error_message="Eine Partnerschaft ist eine Ehe, eine Lebensgemeinschaft oder unbekannt.",
            ),
        )

    def __str__(self) -> str:
        return f"{self.person_a} & {self.person_b}"

    def includes(self, *, person_id: int) -> bool:
        return person_id in (self.person_a_id, self.person_b_id)
