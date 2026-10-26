from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import PersonListEntry
from apps.family_tree.tests.factories.person import PersonFactory

SEPP = PersonListEntry(person=PersonFactory.build(pk=9), name="Sepp Huber", initials="SH", lifespan="* 1931")
TAG = '<c-person.merge-candidates :candidates="candidates" :pk="pk" :search="search" />'


def test_merge_candidates_fetches_the_comparison_with_whoever_is_clicked():
    html = render_component(tag=TAG, context={"candidates": [SEPP], "pk": 7, "search": "sepp"})

    button = parse(html).find("button")
    assert (" ".join(button.get_text().split()), button["data-on:click"]) == (
        "SH Sepp Huber * 1931",
        f"@get('{reverse('family_tree:merge-compare-view', kwargs={'pk': 7, 'other_pk': 9})}')",
    )


def test_merge_candidates_says_when_nobody_matches_the_search():
    html = render_component(tag=TAG, context={"candidates": [], "pk": 7, "search": "Moser"})

    assert parse(html).get_text().strip() == "Niemand im Baum passt zu „Moser“."
