import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.family_tree.models import Note
from apps.family_tree.tests.factories.note import NoteFactory
from apps.family_tree.tests.factories.person import PersonFactory


def test_note_str_names_its_person():
    assert str(NoteFactory.build(person=PersonFactory.build(given_names="Lena", surname="Huber"))) == (
        "Notiz zu Lena Huber"
    )


@pytest.mark.django_db
def test_note_refuses_a_missing_text_on_save():
    with pytest.raises(ValidationError, match="Eine Notiz braucht einen Text"):
        NoteFactory(text="")


@pytest.mark.django_db
def test_note_refuses_a_missing_text_in_the_database():
    person = PersonFactory()

    with pytest.raises(IntegrityError, match="note_has_text"):
        Note.objects.bulk_create([NoteFactory.build(person=person, text="")])
