from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import NoteEntry, NotesTab
from apps.family_tree.tests.factories.note import NoteFactory
from apps.family_tree.tests.factories.person import PersonFactory

LENA = PersonFactory.build(pk=7)


def test_count_says_how_many_notes_there_are():
    notes = [NoteEntry(note=NoteFactory.build(person=LENA), author=None)] * 2

    html = render_component(
        tag='<c-note.count :notes_tab="notes_tab" />', context={"notes_tab": NotesTab(person=LENA, notes=notes)}
    )

    assert parse(html).find(id="person-card-note-count").get_text() == "2"
