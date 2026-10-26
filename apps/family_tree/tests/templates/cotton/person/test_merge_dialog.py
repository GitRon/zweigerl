from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import PersonListEntry
from apps.family_tree.tests.factories.person import PersonFactory

JOSEF = PersonListEntry(person=PersonFactory.build(pk=7), name="Josef Huber", initials="JH", lifespan="* 1931")
TAG = '<c-person.merge-dialog :entry="entry" />'


def test_merge_dialog_names_the_person_and_searches_the_tree_for_the_other():
    page = parse(render_component(tag=TAG, context={"entry": JOSEF}))

    search = page.find("input", attrs={"type": "search"})
    assert (
        page.find("h2").get_text(),
        search["data-bind"],
        search["data-on:input__debounce.300ms"],
    ) == (
        "Josef Huber zusammenführen",
        "merge_search",
        f"@get('{reverse('family_tree:merge-candidates-view', kwargs={'pk': 7})}')",
    )
