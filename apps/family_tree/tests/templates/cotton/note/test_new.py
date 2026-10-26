from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.tests.factories.person import PersonFactory


def test_new_posts_the_note_for_the_person():
    html = render_component(tag='<c-note.new :person="person" />', context={"person": PersonFactory.build(pk=7)})

    form = parse(html).find("form")
    assert (form["data-on:submit"], form.find("textarea")["name"]) == (
        f"@post('{reverse('family_tree:note-create-view', kwargs={'pk': 7})}', {{contentType: 'form'}})",
        "text",
    )
