from dataclasses import replace

from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import LinkPreview, PersonListEntry
from apps.family_tree.tests.factories.person import PersonFactory

PREVIEW = LinkPreview(
    person=PersonListEntry(person=PersonFactory.build(pk=5), name="Lena Huber", initials="LH", lifespan="1990 –"),
    relative=PersonListEntry(person=PersonFactory.build(pk=3), name="Stefan Berger", initials="SB", lifespan="—"),
    relation="partner",
    relation_name="Partner",
    couple_fact_count=0,
)
TAG = '<c-person.unlink-dialog :preview="preview" />'


def test_unlink_dialog_names_the_link_and_posts_its_removal():
    page = parse(render_component(tag=TAG, context={"preview": PREVIEW}))

    url = reverse("family_tree:unlink-view", kwargs={"pk": 5, "relation": "partner", "relative_pk": 3})
    assert (
        "Stefan Berger ist dann nicht mehr Partner von Lena Huber." in page.get_text(),
        page.find("form")["data-on:submit"],
    ) == (True, f"@post('{url}', {{contentType: 'form'}})")


def test_unlink_dialog_says_the_couple_facts_go_with_a_partnership():
    page = parse(render_component(tag=TAG, context={"preview": replace(PREVIEW, couple_fact_count=2)}))

    assert "2 Angaben zum Paar, etwa die Hochzeit, verschwinden mit." in " ".join(page.get_text().split())
