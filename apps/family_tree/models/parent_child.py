from ambient_toolbox.mixins.validation import ValidateConstraintsOnSaveMixin
from django.core.exceptions import ValidationError
from django.db import models

from apps.family_tree.models.gedcom import GedcomRawMixin


class ParentChild(ValidateConstraintsOnSaveMixin, GedcomRawMixin):
    """
    One parent and one child - GEDCOM's CHIL in a FAM, with PEDI as "pedigree". "partnership" names the couple
    the child belongs to, so children of two marriages stay with the right one; a child with one known
    parent has none.
    """

    class Pedigree(models.TextChoices):
        # GEDCOM PEDI: birth, adopted, foster
        BIRTH = "birth", "leiblich"
        ADOPTED = "adopted", "adoptiert"
        FOSTER = "foster", "Pflegekind"
        UNKNOWN = "unknown", "unbekannt"

    MAX_BIRTH_PARENTS = 2

    parent = models.ForeignKey(
        "family_tree.Person", verbose_name="Elternteil", on_delete=models.CASCADE, related_name="child_links"
    )
    child = models.ForeignKey(
        "family_tree.Person", verbose_name="Kind", on_delete=models.CASCADE, related_name="parent_links"
    )
    partnership = models.ForeignKey(
        "family_tree.Partnership",
        verbose_name="Partnerschaft",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_links",
    )
    pedigree = models.CharField("Art", max_length=20, choices=Pedigree, default=Pedigree.BIRTH)

    class Meta:
        verbose_name = "Eltern-Kind-Verbindung"
        verbose_name_plural = "Eltern-Kind-Verbindungen"
        constraints = (
            models.CheckConstraint(
                condition=~models.Q(parent=models.F("child")),
                name="parentchild_not_self",
                violation_error_message="Niemand ist sein eigener Elternteil.",
            ),
            models.UniqueConstraint(
                fields=("parent", "child"),
                name="parentchild_once",
                violation_error_message="Diese Eltern-Kind-Verbindung gibt es schon.",
            ),
            models.CheckConstraint(
                condition=models.Q(pedigree__in=("birth", "adopted", "foster", "unknown")),
                name="parentchild_pedigree_valid",
                violation_error_message="Ein Kind ist leiblich, adoptiert, Pflegekind oder unbekannt.",
            ),
        )

    def __str__(self) -> str:
        return f"{self.parent} → {self.child}"

    @classmethod
    def merged_birth_parents(cls, *, person_id: int, other_id: int) -> set[int]:
        """
        The birth parents "person_id" would have once "other_id" is merged into them (#85): the person's own, and
        those of the other who are no parent of the person yet - a parent of both keeps the person's link, with its
        pedigree. More than two is what the merge refuses.
        """
        parents = cls.objects.filter(child=person_id).values("parent")
        return {
            *cls.objects.filter(child=person_id, pedigree=cls.Pedigree.BIRTH).values_list("parent", flat=True),
            *cls.objects.filter(child=other_id, pedigree=cls.Pedigree.BIRTH)
            .exclude(parent__in=parents)
            .values_list("parent", flat=True),
        }

    def clean(self) -> None:
        """
        The rules across rows no constraint can hold - see docs/patterns/family.md. When the admin adds a
        person together with their parents the child is still unsaved, so what needs the child waits for it;
        a third birth parent among several entered at once is the admin formset's to refuse.
        """
        if self.parent_id is None:
            return
        if self.partnership is not None and not self.partnership.includes(person_id=self.parent_id):
            raise ValidationError({"partnership": "Der Elternteil gehört nicht zu dieser Partnerschaft."})
        if self.child_id is None:
            return
        if self._duplicates_siblings():
            raise ValidationError(
                "Ein anderes Kind dieses Elternteils ist schon als Geschwister ohne bekannte Eltern eingetragen. "
                "Lösche erst diese Geschwister-Verbindung, über den gemeinsamen Elternteil sind die beiden dann "
                "ohnehin Geschwister."
            )
        if self.pedigree == self.Pedigree.BIRTH:
            other_birth_parents = (
                ParentChild.objects.filter(child_id=self.child_id, pedigree=self.Pedigree.BIRTH)
                .exclude(pk=self.pk)
                .count()
            )
            if other_birth_parents >= self.MAX_BIRTH_PARENTS:
                raise ValidationError("Dieses Kind hat schon zwei leibliche Eltern.")

    def _duplicates_siblings(self) -> bool:
        """
        Whether this link would make the child a sibling, through the parent, of someone already stored as
        their explicit sibling - the same fact twice.
        """
        other_children = self.parent.child_links.exclude(child_id=self.child_id).values("child_id")
        return (
            self.child.sibling_pairs_as_a.filter(person_b__in=other_children).exists()
            or self.child.sibling_pairs_as_b.filter(person_a__in=other_children).exists()
        )
