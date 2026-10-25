import pytest

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import PersonListEntry, RelativeCandidates
from apps.family_tree.tests.factories.person import PersonFactory

TAG = '<c-person.candidates :candidates="candidates" :search="search" />'


def _entry(*, person) -> PersonListEntry:
    return PersonListEntry(person=person, name=str(person), initials="LH", lifespan="* 1950")


@pytest.mark.django_db
def test_candidates_offer_each_person_as_a_choice_bound_to_the_relative():
    thomas, josef = PersonFactory.create_batch(2)
    candidates = RelativeCandidates(suggested=[_entry(person=thomas)], found=[_entry(person=josef)])

    html = render_component(tag=TAG, context={"candidates": candidates, "search": "huber"})

    choices = parse(html).find_all("input", attrs={"name": "relative_id"})
    assert [(choice["value"], choice["data-bind"]) for choice in choices] == [
        (str(thomas.pk), "relative"),
        (str(josef.pk), "relative"),
    ]


def test_candidates_say_why_nobody_can_be_chosen():
    candidates = RelativeCandidates(suggested=[], found=[], refusal="Lena Huber hat schon zwei leibliche Eltern.")

    html = render_component(tag=TAG, context={"candidates": candidates, "search": ""})

    assert parse(html).get_text(strip=True) == "Lena Huber hat schon zwei leibliche Eltern."


def test_candidates_say_when_nobody_matches_the_search():
    html = render_component(tag=TAG, context={"candidates": RelativeCandidates(suggested=[], found=[]), "search": "xy"})

    assert parse(html).get_text(strip=True) == "Niemand im Baum passt zu „xy“."


def test_candidates_say_nothing_before_a_search_without_suggestions():
    html = render_component(tag=TAG, context={"candidates": RelativeCandidates(suggested=[], found=[]), "search": ""})

    assert parse(html).get_text(strip=True) == ""
