from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import NoteEntry, NotesTab
from apps.family_tree.tests.factories.note import NoteFactory
from apps.family_tree.tests.factories.person import PersonFactory

TAG = '<c-note.list :notes_tab="notes_tab" />'
LENA = PersonFactory.build(pk=7)


def test_list_shows_each_note_and_the_form_for_a_new_one_with_none_open():
    entry = NoteEntry(note=NoteFactory.build(pk=4, person=LENA, text="Zwei Jahre in Amerika?"), author="Anna")

    html = render_component(tag=TAG, context={"notes_tab": NotesTab(person=LENA, notes=[entry])})

    page = parse(html).find(id="person-card-note-list")
    assert (
        page["data-signals"],
        page.find(id="note-4").find("p").get_text(),
        page.find("form", attrs={"aria-label": "Neue Notiz"}) is not None,
    ) == ("{note: 0}", "Zwei Jahre in Amerika?", True)


def test_list_without_notes_invites_the_first():
    html = render_component(tag=TAG, context={"notes_tab": NotesTab(person=LENA, notes=[])})

    assert "Noch nix notiert. Fragen und Hinweise kommen hierher." in parse(html).get_text()
