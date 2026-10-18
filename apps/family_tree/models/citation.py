from ambient_toolbox.mixins.validation import ValidateConstraintsOnSaveMixin
from django.db import models

from apps.family_tree.models.gedcom import GedcomRawMixin


class Citation(ValidateConstraintsOnSaveMixin, GedcomRawMixin):
    """
    One fact citing one source - a Zitat, GEDCOM's SOUR pointer under a fact with PAGE as "page". A fact
    with a Citation is documented for real; see docs/patterns/evidence.md.
    """

    fact = models.ForeignKey(
        "family_tree.Fact", verbose_name="Angabe", on_delete=models.CASCADE, related_name="citations"
    )
    # PROTECT: a source still cited by a fact does not vanish with it - the citation would be left pointing
    # at nothing and the fact would quietly turn undocumented.
    source = models.ForeignKey(
        "family_tree.Source", verbose_name="Quelle", on_delete=models.PROTECT, related_name="citations"
    )
    page = models.CharField(
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
                fields=("fact", "source"),
                name="citation_once_per_fact_and_source",
                violation_error_message="Diese Angabe zitiert diese Quelle schon.",
            ),
        )

    def __str__(self) -> str:
        return f"{self.fact} - {self.source}"
