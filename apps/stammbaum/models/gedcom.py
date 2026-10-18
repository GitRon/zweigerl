from django.db import models


class GedcomRohMixin(models.Model):
    """
    What a GEDCOM import brought along that Zweigerl does not understand, kept so an export can write it
    back. A list of the raw records as the importer read them (#22); nothing in Zweigerl reads it.
    """

    gedcom_roh = models.JSONField(
        "GEDCOM, roh",
        default=list,
        blank=True,
        help_text="Tags aus einem GEDCOM-Import, die Zweigerl nicht versteht. Werden beim Export wieder geschrieben.",
    )

    class Meta:
        abstract = True
