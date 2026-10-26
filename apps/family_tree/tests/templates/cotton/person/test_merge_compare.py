from dataclasses import replace

from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import PersonListEntry
from apps.family_tree.readers.person_merge import MergeField, MergePreview, MergeSide
from apps.family_tree.tests.factories.person import PersonFactory

JOSEF = MergeSide(
    entry=PersonListEntry(person=PersonFactory.build(pk=7), name="Josef Huber", initials="JH", lifespan="* 1931"),
    origin="PAF Huber",
    fact_count=2,
    photo_count=0,
    note_count=1,
    source_count=1,
    relative_count=3,
)
SEPP = MergeSide(
    entry=PersonListEntry(person=PersonFactory.build(pk=9), name="Sepp Huber", initials="SH", lifespan="* 1931"),
    origin=None,
    fact_count=1,
    photo_count=1,
    note_count=0,
    source_count=0,
    relative_count=2,
)
PREVIEW = MergePreview(
    person=JOSEF,
    other=SEPP,
    fields=[
        MergeField(name="surname", label="Familienname", text="Huber", other_text="Huber"),
        MergeField(name="call_name", label="Rufname", text="", other_text="Sepp"),
    ],
)
TAG = '<c-person.merge-compare :preview="preview" />'


def test_merge_compare_asks_which_differing_field_stays_starting_with_the_person():
    page = parse(render_component(tag=TAG, context={"preview": PREVIEW}))

    person, other = page.find_all("input", attrs={"type": "radio"})
    assert (person["name"], person["value"], person.has_attr("checked"), other["value"], other.has_attr("checked")) == (
        "call_name",
        "person",
        True,
        "other",
        False,
    )


def test_merge_compare_shows_where_each_came_from_and_what_each_brings():
    text = " ".join(parse(render_component(tag=TAG, context={"preview": PREVIEW})).get_text().split())

    assert (
        "Herkunft PAF Huber hier angelegt" in text,
        "2 Angaben, 0 Fotos, 1 Notiz, 1 Quelle, 3 Verwandte" in text,
    ) == (True, True)


def test_merge_compare_posts_the_merge_after_saying_it_cannot_be_undone():
    page = parse(render_component(tag=TAG, context={"preview": PREVIEW}))

    assert (
        page.find("form")["data-on:submit"],
        page.find(role="alert").find("p").get_text(),
    ) == (
        f"@post('{reverse('family_tree:merge-view', kwargs={'pk': 7, 'other_pk': 9})}', {{contentType: 'form'}})",
        "Das lässt sich nicht rückgängig machen",
    )


def test_merge_compare_gives_the_reason_and_no_button_for_two_who_cannot_be_one():
    html = render_component(tag=TAG, context={"preview": replace(PREVIEW, refusal="Die beiden sind ein Paar.")})

    page = parse(html)
    assert (page.find(role="alert").get_text(), page.find("button", attrs={"type": "submit"})) == (
        "Die beiden sind ein Paar.",
        None,
    )
