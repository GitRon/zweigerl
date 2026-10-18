from ambient_toolbox.mixins.validation import ValidateConstraintsOnSaveMixin
from django.db import models

from apps.stammbaum.models.gedcom import GedcomRohMixin


class Zitat(ValidateConstraintsOnSaveMixin, GedcomRohMixin):
    """
    One Angabe citing one Quelle - GEDCOM's SOUR pointer under a fact, with PAGE as "stelle". An Angabe that
    has a Zitat is belegt for real; see docs/patterns/belege.md.
    """

    angabe = models.ForeignKey(
        "stammbaum.Angabe", verbose_name="Angabe", on_delete=models.CASCADE, related_name="zitate"
    )
    # PROTECT: a source still cited by a fact does not vanish with it - the citation would be left pointing
    # at nothing and the fact would quietly turn "unbelegt".
    quelle = models.ForeignKey(
        "stammbaum.Quelle", verbose_name="Quelle", on_delete=models.PROTECT, related_name="zitate"
    )
    stelle = models.CharField(
        "Stelle",
        max_length=300,
        blank=True,
        help_text="Seite, Eintrag oder Stelle in der Quelle, z. B. „Nr. 1989/3471“",
    )

    class Meta:
        verbose_name = "Zitat"
        verbose_name_plural = "Zitate"
        constraints = (
            models.UniqueConstraint(
                fields=("angabe", "quelle"),
                name="zitat_einmal_pro_angabe_und_quelle",
                violation_error_message="Diese Angabe zitiert diese Quelle schon.",
            ),
        )

    def __str__(self) -> str:
        return f"{self.angabe} - {self.quelle}"
