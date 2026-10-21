from ambient_toolbox.mixins.validation import ValidateConstraintsOnSaveMixin
from django.db import models


class GedcomImport(ValidateConstraintsOnSaveMixin, models.Model):
    """
    One GEDCOM file read into the tree (#22), under the name it was given - "PAF Ronny". Every row the import
    wrote points at it as its Herkunft, which the person card shows. The Herkunft is not a Beleg: an imported
    fact without a source of its own stays "unbelegt" - see docs/patterns/evidence.md.
    """

    name = models.CharField("Name", max_length=100)
    imported_at = models.DateTimeField("Importiert am", auto_now_add=True)

    class Meta:
        verbose_name = "Import"
        verbose_name_plural = "Importe"
        ordering = ("imported_at", "pk")
        constraints = (
            models.CheckConstraint(
                condition=~models.Q(name=""),
                name="gedcomimport_has_name",
                violation_error_message="Ein Import braucht einen Namen, etwa „PAF Ronny“.",
            ),
        )

    def __str__(self) -> str:
        return self.name
