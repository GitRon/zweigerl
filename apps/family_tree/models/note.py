from ambient_toolbox.mixins.validation import ValidateConstraintsOnSaveMixin
from django.conf import settings
from django.db import models

from apps.family_tree.models.gedcom import GedcomRawMixin


class Note(ValidateConstraintsOnSaveMixin, GedcomRawMixin):
    """
    A note about a person - a question, a hint, what somebody remembers - GEDCOM's NOTE on an INDI (#23). The
    Notizen tab of the person card shows them (#17). An imported note has no author; its Herkunft says where it
    came from. See docs/patterns/family.md.
    """

    person = models.ForeignKey(
        "family_tree.Person", verbose_name="Person", on_delete=models.CASCADE, related_name="notes"
    )
    text = models.TextField("Text")
    # SET_NULL: a note outlives the account it was written from - the family's notes are not the user's.
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Autor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField("Geschrieben am", auto_now_add=True)
    # None while the note is as it was written - the card shows "bearbeitet" once it is set.
    changed_at = models.DateTimeField("Bearbeitet am", null=True, blank=True)

    class Meta:
        verbose_name = "Notiz"
        verbose_name_plural = "Notizen"
        ordering = ("created_at", "pk")
        constraints = (
            models.CheckConstraint(
                condition=~models.Q(text=""),
                name="note_has_text",
                violation_error_message="Eine Notiz braucht einen Text.",
            ),
        )

    def __str__(self) -> str:
        return f"Notiz zu {self.person}"
