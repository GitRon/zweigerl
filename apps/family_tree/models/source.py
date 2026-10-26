from ambient_toolbox.mixins.validation import ValidateConstraintsOnSaveMixin
from django.db import models

from apps.family_tree.models.gedcom import GedcomRawMixin


class Source(ValidateConstraintsOnSaveMixin, GedcomRawMixin):
    """
    Where facts come from - GEDCOM's SOUR, a Quelle. It stands on its own and is cited by any number of facts
    through a Citation; "people" are the persons it is filed with, so a document can sit on a person's card
    before anything cites it (#15). See docs/patterns/evidence.md.
    """

    class Kind(models.TextChoices):
        CIVIL_REGISTRY = "civil_registry", "Standesamt"
        PARISH_REGISTER = "parish_register", "Matriken"
        FAMILY_TRADITION = "family_tradition", "Familienüberlieferung"
        PHOTOGRAPH = "photograph", "Fotografie"
        CENSUS = "census", "Volkszählung"
        MILITARY = "military", "Militär"
        IMMIGRATION = "immigration", "Einwanderung"
        NEWSPAPER = "newspaper", "Zeitung"
        OTHER = "other", "Sonstiges"

    tree = models.ForeignKey(
        "family_tree.Tree", verbose_name="Stammbaum", on_delete=models.PROTECT, related_name="sources"
    )
    title = models.CharField("Titel", max_length=300)
    kind = models.CharField("Art", max_length=30, choices=Kind, default=Kind.OTHER)
    # What the source says and where it is kept - the mockup's "citation". Not the Citation, which is the
    # link from one fact to this source.
    description = models.TextField("Beschreibung", blank=True)
    people = models.ManyToManyField(
        "family_tree.Person", verbose_name="Abgelegt bei", blank=True, related_name="filed_sources"
    )

    class Meta:
        verbose_name = "Quelle"
        verbose_name_plural = "Quellen"
        ordering = ("title", "pk")
        constraints = (
            models.CheckConstraint(
                condition=~models.Q(title=""),
                name="source_has_title",
                violation_error_message="Eine Quelle braucht einen Titel.",
            ),
            # The values of the choices above, written out: a migration freezes them anyway, and a nested
            # Meta cannot see the enclosing class.
            models.CheckConstraint(
                condition=models.Q(
                    kind__in=(
                        "civil_registry",
                        "parish_register",
                        "family_tradition",
                        "photograph",
                        "census",
                        "military",
                        "immigration",
                        "newspaper",
                        "other",
                    )
                ),
                name="source_kind_valid",
                violation_error_message="Diese Art von Quelle kennt Zweigerl nicht.",
            ),
        )

    def __str__(self) -> str:
        return self.title
