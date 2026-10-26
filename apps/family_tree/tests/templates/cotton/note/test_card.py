import datetime
from dataclasses import replace

from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import NoteEntry
from apps.family_tree.tests.factories.note import NoteFactory
from apps.family_tree.tests.factories.person import PersonFactory

TAG = '<c-note.card :entry="entry" :person="person" />'
LENA = PersonFactory.build(pk=7)
WRITTEN = datetime.datetime(2026, 3, 12, 14, 5, tzinfo=datetime.UTC)
ENTRY = NoteEntry(
    note=NoteFactory.build(pk=4, person=LENA, text="Zwei Jahre in Amerika?", created_at=WRITTEN), author="Anna Huber"
)


def _byline(entry: NoteEntry) -> str:
    html = render_component(tag=TAG, context={"entry": entry, "person": LENA})

    return " ".join(parse(html).find(id="note-4").find("time").find_parent("p").get_text().split())


def test_card_shows_the_text_in_handwriting_with_author_and_time():
    html = render_component(tag=TAG, context={"entry": ENTRY, "person": LENA})

    note = parse(html).find(id="note-4")
    assert (note.find("p").get_text(), _byline(ENTRY)) == (
        "Zwei Jahre in Amerika?",
        "Anna Huber · 12. März 2026, 15:05",
    )


def test_card_says_an_edited_note_is_edited():
    entry = replace(ENTRY, note=NoteFactory.build(pk=4, person=LENA, created_at=WRITTEN, changed_at=WRITTEN))

    assert _byline(entry).endswith("· bearbeitet")


def test_card_names_the_import_of_a_note_without_author():
    assert _byline(replace(ENTRY, author=None, origin="PAF Huber")).startswith("Herkunft: PAF Huber ·")


def test_card_names_no_author_once_the_account_is_gone():
    assert _byline(replace(ENTRY, author=None)).startswith("Unbekannt ·")


def test_card_opens_its_form_with_the_pencil_and_posts_the_change():
    html = render_component(tag=TAG, context={"entry": ENTRY, "person": LENA})

    page = parse(html)
    form = page.find("form", attrs={"aria-label": "Notiz bearbeiten"})
    url = reverse("family_tree:note-change-view", kwargs={"pk": 7, "note_pk": 4})
    assert (
        page.find("button", attrs={"aria-label": "Notiz bearbeiten"})["data-on:click"],
        form["data-show"],
        form["data-on:submit"],
        form.find("textarea", attrs={"name": "text"}).get_text(),
        form.find("button", string="Abbrechen")["data-on:click"],
    ) == ("$note = 4", "$note == 4", f"@post('{url}', {{contentType: 'form'}})", "Zwei Jahre in Amerika?", "$note = 0")


def test_card_asks_before_deleting_the_note():
    html = render_component(tag=TAG, context={"entry": ENTRY, "person": LENA})

    assert parse(html).find("button", attrs={"aria-label": "Notiz löschen"})["data-on:click"] == (
        f"@get('{reverse('family_tree:delete-note-view', kwargs={'pk': 7, 'note_pk': 4})}')"
    )
