import pytest
from django.core.exceptions import ValidationError

from apps.family_tree.actions.note import change_note, create_note, delete_note
from apps.family_tree.models import Note, Person
from apps.family_tree.tests.factories.note import NoteFactory
from apps.family_tree.tests.factories.person import PersonFactory


@pytest.mark.django_db
def test_create_note_writes_the_note_signed_by_its_author(django_user_model):
    lena = PersonFactory()
    anna = django_user_model.objects.create_user(username="anna")

    note = create_note(person_id=lena.pk, author_id=anna.pk, text="  Im Passagierregister suchen.\n")

    assert list(Note.objects.values_list("person", "author", "text", "changed_at")) == [
        (lena.pk, anna.pk, "Im Passagierregister suchen.", None)
    ]
    assert note.pk is not None


@pytest.mark.django_db
def test_create_note_refuses_somebody_not_in_the_tree():
    with pytest.raises(Person.DoesNotExist):
        create_note(person_id=404, author_id=None, text="Im Passagierregister suchen.")


@pytest.mark.django_db
def test_create_note_refuses_a_note_without_text():
    lena = PersonFactory()

    with pytest.raises(ValidationError, match=r"Eine Notiz braucht einen Text\."):
        create_note(person_id=lena.pk, author_id=None, text="   ")

    assert Note.objects.exists() is False


@pytest.mark.django_db
def test_change_note_saves_the_text_and_marks_it_edited():
    note = NoteFactory(text="Zwei Jahre in Amerika?")

    change_note(person_id=note.person.pk, note_id=note.pk, text="Drei Jahre in Amerika.")

    note.refresh_from_db()
    assert (note.text, note.changed_at is not None) == ("Drei Jahre in Amerika.", True)


@pytest.mark.django_db
def test_change_note_with_the_same_text_does_not_mark_it_edited():
    note = NoteFactory(text="Zwei Jahre in Amerika?")

    change_note(person_id=note.person.pk, note_id=note.pk, text=" Zwei Jahre in Amerika? ")

    note.refresh_from_db()
    assert note.changed_at is None


@pytest.mark.django_db
def test_change_note_refuses_a_note_of_somebody_else():
    note = NoteFactory()

    with pytest.raises(Note.DoesNotExist):
        change_note(person_id=PersonFactory().pk, note_id=note.pk, text="Anders.")


@pytest.mark.django_db
def test_change_note_refuses_an_emptied_text():
    note = NoteFactory(text="Zwei Jahre in Amerika?")

    with pytest.raises(ValidationError, match=r"Eine Notiz braucht einen Text\."):
        change_note(person_id=note.person.pk, note_id=note.pk, text="")

    note.refresh_from_db()
    assert (note.text, note.changed_at) == ("Zwei Jahre in Amerika?", None)


@pytest.mark.django_db
def test_delete_note_deletes_the_note():
    note = NoteFactory()
    kept = NoteFactory(person=note.person)

    delete_note(person_id=note.person.pk, note_id=note.pk)

    assert list(Note.objects.all()) == [kept]


@pytest.mark.django_db
def test_delete_note_refuses_a_note_of_somebody_else():
    note = NoteFactory()

    with pytest.raises(Note.DoesNotExist):
        delete_note(person_id=PersonFactory().pk, note_id=note.pk)
