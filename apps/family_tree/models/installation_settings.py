from ambient_toolbox.mixins.validation import ValidateConstraintsOnSaveMixin
from django.db import models


class InstallationSettings(ValidateConstraintsOnSaveMixin, models.Model):
    """
    The settings of the installation as a whole, whichever tree is open (#34): one row, primary key 1. The folder
    backups go to (#27) and when the last one was written (#33) - a backup holds every tree. What belongs to one
    tree, its home person, is on the "Tree".
    """

    ONLY_ROW = 1

    id = models.PositiveSmallIntegerField(primary_key=True, default=ONLY_ROW, editable=False)
    # Where "manage.py backup" and the settings page's button write their timestamped folders (#27, #33). Outside
    # the data directory and the repository - the action refuses both.
    backup_dir = models.CharField("Sicherungsordner", max_length=500, blank=True)
    # The moment the last finished backup is named after, wherever it went - the settings' folder or "--target" -
    # for "Zuletzt gesichert" in the sidebar (#33). Empty until the first one.
    last_backup_at = models.DateTimeField("Zuletzt gesichert", null=True, blank=True)

    class Meta:
        verbose_name = "Einstellung"
        verbose_name_plural = "Einstellungen"
        constraints = (
            models.CheckConstraint(
                condition=models.Q(id=1),
                name="installationsettings_single_row",
                violation_error_message="Es gibt nur eine Zeile Einstellungen.",
            ),
        )

    def __str__(self) -> str:
        return "Einstellungen der Installation"
