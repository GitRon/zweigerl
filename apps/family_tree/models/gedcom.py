from django.db import models


class GedcomRawMixin(models.Model):
    """
    What a GEDCOM import brought along that Zweigerl does not understand, kept so the export writes it back
    (#22, #26): a list of GEDCOM structures {"tag", "value", "children"} - see docs/patterns/gedcom.md, "Raw
    GEDCOM". Nothing in Zweigerl but the export reads it.
    """

    gedcom_raw = models.JSONField(
        "GEDCOM, roh",
        default=list,
        blank=True,
        help_text="Tags aus einem GEDCOM-Import, die Zweigerl nicht versteht. Werden beim Export wieder geschrieben.",
    )

    class Meta:
        abstract = True
