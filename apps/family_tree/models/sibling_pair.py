from ambient_toolbox.mixins.validation import ValidateConstraintsOnSaveMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Greatest, Least

from apps.family_tree.models.gedcom import GedcomRawMixin


class SiblingPair(ValidateConstraintsOnSaveMixin, GedcomRawMixin):
    """
    Two siblings whose shared parents nobody knows - in GEDCOM a FAM with children and no parents. Siblings
    with a known shared parent are siblings through it and are never stored here: a second way to say the
    same thing is a second thing to keep in step. Stored once per pair, either way round.
    """

    person_a = models.ForeignKey(
        "family_tree.Person", verbose_name="Person", on_delete=models.CASCADE, related_name="sibling_pairs_as_a"
    )
    person_b = models.ForeignKey(
        "family_tree.Person", verbose_name="Geschwister", on_delete=models.CASCADE, related_name="sibling_pairs_as_b"
    )

    class Meta:
        verbose_name = "Geschwister ohne bekannte Eltern"
        verbose_name_plural = "Geschwister ohne bekannte Eltern"
        constraints = (
            models.CheckConstraint(
                condition=~models.Q(person_a=models.F("person_b")),
                name="siblingpair_not_self",
                violation_error_message="Niemand ist sein eigenes Geschwister.",
            ),
            # On the pair rather than on the two columns, so B & A is refused once A & B exists.
            models.UniqueConstraint(
                Least("person_a", "person_b"),
                Greatest("person_a", "person_b"),
                name="siblingpair_once_per_pair",
                violation_error_message="Diese beiden sind schon als Geschwister eingetragen.",
            ),
        )

    def __str__(self) -> str:
        return f"{self.person_a} & {self.person_b}"

    def clean(self) -> None:
        """
        The rule across rows no constraint can hold - see docs/patterns/family.md.
        """
        if self.person_a_id is None or self.person_b_id is None:
            return
        if self.person_a.parent_links.filter(parent__child_links__child=self.person_b_id).exists():
            raise ValidationError("Die beiden haben einen gemeinsamen Elternteil und sind darüber schon Geschwister.")
