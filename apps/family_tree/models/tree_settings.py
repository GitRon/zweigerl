from ambient_toolbox.mixins.validation import ValidateConstraintsOnSaveMixin
from django.db import models


class TreeSettings(ValidateConstraintsOnSaveMixin, models.Model):
    """
    The settings of the one tree an installation holds (#34 brings several): one row, primary key 1.
    The home person ("Ausgangsperson"), which the tree is laid out around (#11) and which #18, #19 and #20 read,
    and the folder backups go to (#27).
    """

    ONLY_ROW = 1

    id = models.PositiveSmallIntegerField(primary_key=True, default=ONLY_ROW, editable=False)
    # PROTECT: the tree is built around this person, so deleting them is refused until another one is
    # chosen (#19).
    home_person = models.ForeignKey(
        "family_tree.Person",
        verbose_name="Ausgangsperson",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    # Where "manage.py backup" writes its timestamped folders (#27); the settings page edits it with #33. Outside
    # the data directory and the repository - the action refuses both.
    backup_dir = models.CharField("Sicherungsordner", max_length=500, blank=True)

    class Meta:
        verbose_name = "Einstellung"
        verbose_name_plural = "Einstellungen"
        constraints = (
            models.CheckConstraint(
                condition=models.Q(id=1),
                name="treesettings_single_row",
                violation_error_message="Es gibt nur eine Zeile Einstellungen.",
            ),
        )

    def __str__(self) -> str:
        return "Einstellungen des Stammbaums"
