from django.core.exceptions import ValidationError
from django.db import models

from apps.stammbaum.models.gedcom import GedcomRohMixin
from apps.stammbaum.models.paar import GeordnetesPaarMixin


class Geschwister(GeordnetesPaarMixin, GedcomRohMixin):
    """
    Two siblings whose shared parents nobody knows - in GEDCOM a FAM with children and no parents. Siblings
    with a known shared parent are siblings through it and are never stored here: a second way to say the
    same thing is a second thing to keep in step. Stored once per pair, the lower primary key first.
    """

    person_a = models.ForeignKey(
        "stammbaum.Person", verbose_name="Person", on_delete=models.CASCADE, related_name="geschwister_als_a"
    )
    person_b = models.ForeignKey(
        "stammbaum.Person", verbose_name="Geschwister", on_delete=models.CASCADE, related_name="geschwister_als_b"
    )

    class Meta:
        verbose_name = "Geschwister ohne bekannte Eltern"
        verbose_name_plural = "Geschwister ohne bekannte Eltern"
        constraints = (
            models.CheckConstraint(
                condition=models.Q(person_a__lt=models.F("person_b")), name="geschwister_paar_geordnet"
            ),
            models.UniqueConstraint(fields=("person_a", "person_b"), name="geschwister_einmal_pro_paar"),
        )

    def __str__(self) -> str:
        return f"{self.person_a} & {self.person_b}"

    def clean(self) -> None:
        if self.person_a_id is None or self.person_b_id is None:
            return
        if self.person_a_id == self.person_b_id:
            raise ValidationError("Niemand ist sein eigenes Geschwister.")
        eltern_a = set(self.person_a.eltern_verbindungen.values_list("elternteil_id", flat=True))
        eltern_b = set(self.person_b.eltern_verbindungen.values_list("elternteil_id", flat=True))
        if eltern_a & eltern_b:
            raise ValidationError("Die beiden haben einen gemeinsamen Elternteil und sind darüber schon Geschwister.")
        self.ordne_paar()
