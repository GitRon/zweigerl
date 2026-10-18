import pytest

from apps.common.tests.html import parse, render_component
from apps.family_tree.actions.person import Relation
from apps.family_tree.models import Person

TAG = (
    '<c-person.new-dialog title="Verwandte von Lena Huber hinzufügen" url="/persons/7/relatives/" '
    ':relations="relations" :sexes="sexes" :living_statuses="living_statuses" />'
)
CHOICES = {"sexes": Person.Sex.choices, "living_statuses": Person.LivingStatus.choices}


def test_new_dialog_opens_itself_and_goes_away_when_closed():
    html = render_component(tag=TAG, context={"relations": [], **CHOICES})

    dialog = parse(html).find("dialog")
    assert (dialog["data-init"], dialog["data-on:close"]) == ("el.showModal()", "el.remove()")


def test_new_dialog_posts_the_form_to_its_url():
    html = render_component(tag=TAG, context={"relations": [], **CHOICES})

    page = parse(html)
    assert page.find("form")["data-on:submit"] == "@post('/persons/7/relatives/', {contentType: 'form'})"
    assert page.find("h2").get_text() == "Verwandte von Lena Huber hinzufügen"


@pytest.mark.parametrize("relation", ["parent", "partner", "child", "sibling"])
def test_new_dialog_asks_for_the_relation_when_given_some(relation):
    html = render_component(tag=TAG, context={"relations": Relation.choices, **CHOICES})

    radio = parse(html).find("input", attrs={"name": "relation", "value": relation})
    assert radio.has_attr("required") is True


def test_new_dialog_asks_for_no_relation_without_any():
    html = render_component(tag=TAG, context={"relations": [], **CHOICES})

    assert parse(html).find("input", attrs={"name": "relation"}) is None


def test_new_dialog_starts_with_sex_and_living_status_unknown():
    html = render_component(tag=TAG, context={"relations": [], **CHOICES})

    page = parse(html)
    assert page.find("input", attrs={"name": "sex", "checked": True})["value"] == "U"
    assert page.find("input", attrs={"name": "living_status", "checked": True})["value"] == "unknown"


def test_new_dialog_closes_on_cancel():
    html = render_component(tag=TAG, context={"relations": [], **CHOICES})

    assert parse(html).find("button", string="Abbrechen")["data-on:click"] == "el.closest('dialog').close()"
