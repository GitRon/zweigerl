from django.core.exceptions import ValidationError
from django.db import models

from apps.stammbaum.models.gedcom import GedcomRohMixin


class ElternKind(GedcomRohMixin):
    """
    One parent and one child - GEDCOM's CHIL in a FAM, with PEDI as "art". "partnerschaft" names the couple
    the child belongs to, so children of two marriages stay with the right one; a child with one known
    parent has none.
    """

    class Art(models.TextChoices):
        # GEDCOM PEDI: birth, adopted, foster
        LEIBLICH = "leiblich", "leiblich"
        ADOPTIERT = "adoptiert", "adoptiert"
        PFLEGE = "pflege", "Pflegekind"
        UNBEKANNT = "unbekannt", "unbekannt"

    MAX_LEIBLICHE_ELTERN = 2

    elternteil = models.ForeignKey(
        "stammbaum.Person", verbose_name="Elternteil", on_delete=models.CASCADE, related_name="kind_verbindungen"
    )
    kind = models.ForeignKey(
        "stammbaum.Person", verbose_name="Kind", on_delete=models.CASCADE, related_name="eltern_verbindungen"
    )
    partnerschaft = models.ForeignKey(
        "stammbaum.Partnerschaft",
        verbose_name="Partnerschaft",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kind_verbindungen",
    )
    art = models.CharField("Art", max_length=20, choices=Art, default=Art.LEIBLICH)

    class Meta:
        verbose_name = "Eltern-Kind-Verbindung"
        verbose_name_plural = "Eltern-Kind-Verbindungen"
        constraints = (
            models.CheckConstraint(condition=~models.Q(elternteil=models.F("kind")), name="elternkind_nicht_selbst"),
            models.UniqueConstraint(fields=("elternteil", "kind"), name="elternkind_einmal"),
        )

    def __str__(self) -> str:
        return f"{self.elternteil} → {self.kind}"

    def clean(self) -> None:
        if self.elternteil_id is None or self.kind_id is None:
            return
        if self.elternteil_id == self.kind_id:
            raise ValidationError("Niemand ist sein eigener Elternteil.")
        if self.partnerschaft is not None and not self.partnerschaft.enthaelt(person_id=self.elternteil_id):
            raise ValidationError({"partnerschaft": "Der Elternteil gehört nicht zu dieser Partnerschaft."})
        if self.art == self.Art.LEIBLICH:
            andere_leibliche = (
                ElternKind.objects.filter(kind_id=self.kind_id, art=self.Art.LEIBLICH).exclude(pk=self.pk).count()
            )
            if andere_leibliche >= self.MAX_LEIBLICHE_ELTERN:
                raise ValidationError("Dieses Kind hat schon zwei leibliche Eltern.")
