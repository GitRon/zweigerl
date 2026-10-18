from ambient_toolbox.mixins.validation import ValidateConstraintsOnSaveMixin
from django.db import models


class Einstellung(ValidateConstraintsOnSaveMixin, models.Model):
    """
    The settings of the one tree an installation holds (#34 brings several): one row, primary key 1.
    For now only the Ausgangsperson, which the tree is laid out around (#11) and which #18, #19 and #20 read.
    """

    EINZIGE_ZEILE = 1

    id = models.PositiveSmallIntegerField(primary_key=True, default=EINZIGE_ZEILE, editable=False)
    # PROTECT: the tree is built around this person, so deleting them is refused until another one is
    # chosen (#19).
    ausgangsperson = models.ForeignKey(
        "stammbaum.Person",
        verbose_name="Ausgangsperson",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        verbose_name = "Einstellung"
        verbose_name_plural = "Einstellungen"
        constraints = (
            models.CheckConstraint(
                condition=models.Q(id=1),
                name="einstellung_nur_eine_zeile",
                violation_error_message="Es gibt nur eine Zeile Einstellungen.",
            ),
        )

    def __str__(self) -> str:
        return "Einstellungen des Stammbaums"
