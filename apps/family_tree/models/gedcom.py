from django.db import models


class GedcomRawMixin(models.Model):
    """
    What a GEDCOM import brought along: which import the row came from, and what Zweigerl does not understand,
    kept so the export writes it back (#22, #26) - a list of GEDCOM structures {"tag", "value", "children"}, see
    docs/patterns/gedcom.md, "Raw GEDCOM". Nothing in Zweigerl but the export reads the raw structures.
    """

    gedcom_raw = models.JSONField(
        "GEDCOM, roh",
        default=list,
        blank=True,
        help_text="Tags aus einem GEDCOM-Import, die Zweigerl nicht versteht. Werden beim Export wieder geschrieben.",
    )
    # PROTECT: the Herkunft of a row does not vanish while the row is there. No reverse accessor: an import is
    # never asked for its rows, and one accessor per model would need a name of its own each.
    gedcom_import = models.ForeignKey(
        "family_tree.GedcomImport",
        verbose_name="Herkunft",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Der Import, aus dem diese Zeile stammt. Kein Beleg.",
    )

    class Meta:
        abstract = True
