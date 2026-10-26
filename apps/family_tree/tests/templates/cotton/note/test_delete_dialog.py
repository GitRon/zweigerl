from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import NoteEntry
from apps.family_tree.tests.factories.note import NoteFactory

TAG = '<c-note.delete-dialog :entry="entry" :url="url" />'


def test_delete_dialog_shows_the_note_and_posts_the_deletion():
    entry = NoteEntry(note=NoteFactory.build(pk=4, text="Zwei Jahre in Amerika?"), author=None)
    url = reverse("family_tree:delete-note-view", kwargs={"pk": 7, "note_pk": 4})

    page = parse(render_component(tag=TAG, context={"entry": entry, "url": url}))

    assert (page.find("h2").get_text(), page.find("p").get_text(), page.find("form")["data-on:submit"]) == (
        "Notiz löschen?",
        "Zwei Jahre in Amerika?",
        f"@post('{url}', {{contentType: 'form'}})",
    )
