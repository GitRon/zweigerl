from dataclasses import replace

from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import DeletionPreview, PersonListEntry, RelativeEntry, RelativeGroup
from apps.family_tree.tests.factories.person import PersonFactory

JOHANN = PersonListEntry(person=PersonFactory.build(pk=3), name="Johann Huber", initials="JH", lifespan="1931 – 2009")
LENA = PersonListEntry(person=PersonFactory.build(pk=5), name="Lena Huber", initials="LH", lifespan="1990 –")
FRANZ = PersonListEntry(person=PersonFactory.build(pk=8), name="Franz Huber", initials="FH", lifespan="—")
PREVIEW = DeletionPreview(
    entry=JOHANN,
    home=False,
    fact_count=2,
    citation_count=1,
    source_count=1,
    relatives=[RelativeGroup(title="Kinder", relation="child", entries=[RelativeEntry(entry=LENA, unlinkable=True)])],
    cut_off=[],
)
TAG = '<c-person.delete-dialog :preview="preview" />'


def test_delete_dialog_says_what_vanishes_what_stays_and_which_links_go():
    text = " ".join(parse(render_component(tag=TAG, context={"preview": PREVIEW})).get_text().split())

    assert (
        "2 Angaben mit 1 Beleg" in text,
        "1 Quelle von Johann Huber bleibt erhalten" in text,
        "Lena Huber (Kinder)" in text,
    ) == (True, True, True)


def test_delete_dialog_posts_the_deletion():
    form = parse(render_component(tag=TAG, context={"preview": PREVIEW})).find("form")

    assert form["data-on:submit"] == (
        f"@post('{reverse('family_tree:delete-person-view', kwargs={'pk': 3})}', {{contentType: 'form'}})"
    )


def test_delete_dialog_waits_for_the_tick_when_people_would_hang_loose():
    html = render_component(tag=TAG, context={"preview": replace(PREVIEW, cut_off=[FRANZ, LENA])})

    page = parse(html)
    tick = page.find("input", attrs={"name": "loose_accepted"})
    assert (
        tick.has_attr("required"),
        tick["value"],
        " ".join(tick.find_parent("label").get_text().split()),
        "Franz Huber" in page.find(role="alert").get_text(),
    ) == (True, "2", "Ist mir klar: 2 Personen hängen dann lose", True)


def test_delete_dialog_asks_for_no_tick_when_nobody_hangs_loose():
    html = render_component(tag=TAG, context={"preview": replace(PREVIEW, relatives=[], source_count=0)})

    assert parse(html).find("input", attrs={"name": "loose_accepted"}) is None


def test_delete_dialog_of_the_home_person_leads_to_choosing_another_one():
    page = parse(render_component(tag=TAG, context={"preview": replace(PREVIEW, home=True)}))

    assert (page.find("form"), page.find("a", string="Andere Ausgangsperson wählen…")["href"]) == (
        None,
        reverse("family_tree:tree-settings-view"),
    )
