from ambient_toolbox.mixins.validation import ValidateConstraintsOnSaveMixin
from django.core.exceptions import ValidationError
from django.db import models


class Tree(ValidateConstraintsOnSaveMixin, models.Model):
    """
    One family tree (#34) - the family of one's partner gets a tree of its own rather than a second installation.
    Every person, source, photo and import belongs to exactly one, and everything else belongs through them; the
    trees never share anybody. See docs/patterns/family.md.
    """

    name = models.CharField("Name", max_length=100)
    # The Ausgangsperson, whom the tree is laid out around (#11) and relationships are named from (#20). PROTECT:
    # deleting them is refused until another one is chosen (#19).
    home_person = models.ForeignKey(
        "family_tree.Person",
        verbose_name="Ausgangsperson",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        verbose_name = "Stammbaum"
        verbose_name_plural = "Stammbäume"
        ordering = ("name", "pk")
        constraints = (
            models.CheckConstraint(
                condition=~models.Q(name=""),
                name="tree_has_name",
                violation_error_message="Ein Stammbaum braucht einen Namen, etwa „Familie Huber“.",
            ),
            models.UniqueConstraint(
                fields=("name",),
                name="tree_name_once",
                violation_error_message="Einen Stammbaum mit diesem Namen gibt es schon.",
            ),
        )

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        """
        The home person is somebody of this tree - a rule across two rows, see docs/patterns/family.md.
        """
        if self.home_person is not None and self.home_person.tree_id != self.pk:
            raise ValidationError({"home_person": "Die Ausgangsperson gehört zu einem anderen Stammbaum."})
