from ambient_toolbox.mixins.validation import ValidateConstraintsOnSaveMixin
from django.db import models

from apps.stammbaum.models.gedcom import GedcomRohMixin


class Quelle(ValidateConstraintsOnSaveMixin, GedcomRohMixin):
    """
    Where facts come from - GEDCOM's SOUR. It stands on its own and is cited by any number of Angaben through
    a Zitat; "personen" are the people it is filed with, so a document can sit on a person's card before
    anything cites it (#15). See docs/patterns/belege.md.
    """

    class Art(models.TextChoices):
        STANDESAMT = "standesamt", "Standesamt"
        MATRIKEN = "matriken", "Matriken"
        FAMILIENUEBERLIEFERUNG = "familienueberlieferung", "Familienüberlieferung"
        FOTOGRAFIE = "fotografie", "Fotografie"
        VOLKSZAEHLUNG = "volkszaehlung", "Volkszählung"
        MILITAER = "militaer", "Militär"
        EINWANDERUNG = "einwanderung", "Einwanderung"
        ZEITUNG = "zeitung", "Zeitung"
        SONSTIGES = "sonstiges", "Sonstiges"

    titel = models.CharField("Titel", max_length=300)
    art = models.CharField("Art", max_length=30, choices=Art, default=Art.SONSTIGES)
    # What the source says and where it is kept - the mockup's "citation". Not the Zitat, which is the link
    # from one Angabe to this source.
    beschreibung = models.TextField("Beschreibung", blank=True)
    personen = models.ManyToManyField(
        "stammbaum.Person", verbose_name="Abgelegt bei", blank=True, related_name="abgelegte_quellen"
    )

    class Meta:
        verbose_name = "Quelle"
        verbose_name_plural = "Quellen"
        ordering = ("titel", "pk")
        constraints = (
            models.CheckConstraint(
                condition=~models.Q(titel=""),
                name="quelle_hat_titel",
                violation_error_message="Eine Quelle braucht einen Titel.",
            ),
            # The values of the choices above, written out: a migration freezes them anyway, and a nested
            # Meta cannot see the enclosing class.
            models.CheckConstraint(
                condition=models.Q(
                    art__in=(
                        "standesamt",
                        "matriken",
                        "familienueberlieferung",
                        "fotografie",
                        "volkszaehlung",
                        "militaer",
                        "einwanderung",
                        "zeitung",
                        "sonstiges",
                    )
                ),
                name="quelle_art_gueltig",
                violation_error_message="Diese Art von Quelle kennt Zweigerl nicht.",
            ),
        )

    def __str__(self) -> str:
        return self.titel
