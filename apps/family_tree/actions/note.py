from django.db import transaction
from django.utils import timezone

from apps.family_tree.models import Note, Person


def create_note(*, person_id: int, author_id: int | None, text: str) -> Note:
    """
    Writes a note on the person from the Notizen tab of their card (#17), signed by "author_id". Raises
    "Person.DoesNotExist" for somebody no longer in the tree and "ValidationError" for a note without a text.
    """
    with transaction.atomic():
        person = Person.objects.get(pk=person_id)
        note = Note(person=person, author_id=author_id, text=text.strip())
        note.save()

    return note


def change_note(*, person_id: int, note_id: int, text: str) -> Note:
    """
    Saves a note of the person as changed on their card (#17), marking it "bearbeitet" - unless the text is the
    same as before, which changes nothing. The author stays the one who wrote it. Raises "Note.DoesNotExist" for
    a note that is not the person's or already gone and "ValidationError" for a text emptied out.
    """
    with transaction.atomic():
        note = Note.objects.select_for_update().get(pk=note_id, person_id=person_id)
        text = text.strip()
        if text != note.text:
            note.text = text
            note.changed_at = timezone.now()
            note.save()

    return note


def delete_note(*, person_id: int, note_id: int) -> Note:
    """
    Deletes a note of the person (#17). Raises "Note.DoesNotExist" for a note that is not theirs or already gone.
    """
    note = Note.objects.get(pk=note_id, person_id=person_id)
    note.delete()

    return note
