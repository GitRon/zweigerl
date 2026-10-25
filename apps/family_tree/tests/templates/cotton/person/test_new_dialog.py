import pytest

from apps.common.tests.html import parse, render_component
from apps.family_tree.actions.person import Relation
from apps.family_tree.models import Person
from apps.family_tree.readers.person import Couple

TAG = (
    '<c-person.new-dialog title="Verwandte von Lena Huber hinzufügen" url="/persons/7/relatives/" '
    ':relations="relations" :couples="couples" :sexes="sexes" :living_statuses="living_statuses" />'
)
RELATIVE_TAG = (
    '<c-person.new-dialog title="Verwandte von Lena Huber hinzufügen" url="/persons/7/relatives/" '
    ':relations="relations" :couples="couples" :sexes="sexes" :living_statuses="living_statuses" '
    'person_name="Lena Huber" :parent_name="parent_name" candidates_url="/persons/7/relatives/candidates/" />'
)
CHOICES = {"sexes": Person.Sex.choices, "living_statuses": Person.LivingStatus.choices}
NEW_PERSON = {"relations": [], "couples": [], **CHOICES}
RELATIVE = {"relations": Relation.choices, "couples": [], "parent_name": "", **CHOICES}


def test_new_dialog_opens_itself_and_goes_away_when_closed():
    html = render_component(tag=TAG, context=NEW_PERSON)

    dialog = parse(html).find("dialog")
    assert (dialog["data-init"], dialog["data-on:close"]) == ("el.showModal()", "el.remove()")


def test_new_dialog_keeps_escape_from_closing_the_card_behind_it():
    html = render_component(tag=TAG, context=NEW_PERSON)

    assert parse(html).find("dialog")["data-on:keydown"] == "evt.key == 'Escape' && evt.stopPropagation()"


def test_new_dialog_posts_the_form_to_its_url():
    html = render_component(tag=TAG, context=NEW_PERSON)

    page = parse(html)
    assert page.find("form")["data-on:submit"] == "@post('/persons/7/relatives/', {contentType: 'form'})"
    assert page.find("h2").get_text() == "Verwandte von Lena Huber hinzufügen"


@pytest.mark.parametrize("relation", ["parent", "partner", "child", "sibling"])
def test_new_dialog_asks_for_the_relation_and_fetches_whom_the_tree_offers(relation):
    html = render_component(tag=RELATIVE_TAG, context=RELATIVE)

    radio = parse(html).find("input", attrs={"name": "relation", "value": relation})
    assert radio.has_attr("required") is True
    assert radio["data-on:change"] == (
        "$relation = el.value; $relative = ''; @get('/persons/7/relatives/candidates/')"
    )


def test_new_dialog_searches_the_tree_for_the_relative():
    html = render_component(tag=RELATIVE_TAG, context=RELATIVE)

    search = parse(html).find("input", attrs={"type": "search"})
    assert (search["data-bind"], search["data-on:input__debounce.300ms"]) == (
        "relative_search",
        "@get('/persons/7/relatives/candidates/')",
    )


def test_new_dialog_offers_a_new_person_below_the_tree():
    html = render_component(tag=RELATIVE_TAG, context=RELATIVE)

    page = parse(html)
    new = page.find("input", attrs={"name": "relative_id", "value": ""})
    assert (new["data-bind"], new.parent.get_text(strip=True)) == ("relative", "Neue Person anlegen")
    assert page.find("input", attrs={"name": "given_names"}).find_parent("div")["data-show"] == "$relative == ''"


def test_new_dialog_asks_whose_child_with_one_couple_preselected():
    couples = [Couple(partnership_id=3, partner="Stefan Huber")]
    html = render_component(tag=RELATIVE_TAG, context={**RELATIVE, "couples": couples})

    page = parse(html)
    choices = page.find_all("input", attrs={"name": "partnership"})
    assert [(choice["value"], choice.has_attr("checked")) for choice in choices] == [("3", True), ("", False)]
    assert [choice.parent.get_text(strip=True) for choice in choices] == [
        "Lena Huber und Stefan Huber",
        "nur von Lena Huber",
    ]
    assert choices[0].find_parent("fieldset")["data-show"] == "$relation == 'child'"


def test_new_dialog_preselects_no_couple_of_several():
    couples = [Couple(partnership_id=3, partner="Stefan Huber"), Couple(partnership_id=4, partner="Jan Berger")]
    html = render_component(tag=RELATIVE_TAG, context={**RELATIVE, "couples": couples})

    choices = parse(html).find_all("input", attrs={"name": "partnership"})
    assert [choice.has_attr("checked") for choice in choices] == [False, False, False]
    assert {choice["data-attr:required"] for choice in choices} == {"$relation == 'child'"}


def test_new_dialog_asks_whether_a_second_parent_is_a_couple_with_the_first():
    html = render_component(tag=RELATIVE_TAG, context={**RELATIVE, "parent_name": "Maria Huber"})

    pair = parse(html).find("input", attrs={"name": "pair_with_parent"})
    assert (pair.has_attr("checked"), pair.parent.get_text(strip=True)) == (True, "Mit Maria Huber ein Paar")
    assert pair.parent["data-show"] == "$relation == 'parent'"


def test_new_dialog_asks_no_couple_question_without_couples_or_a_parent():
    html = render_component(tag=RELATIVE_TAG, context=RELATIVE)

    page = parse(html)
    assert (page.find("input", attrs={"name": "partnership"}), page.find("input", attrs={"name": "pair_with_parent"})) == (
        None,
        None,
    )


def test_new_dialog_asks_for_no_relation_without_any():
    html = render_component(tag=TAG, context=NEW_PERSON)

    page = parse(html)
    assert (page.find("input", attrs={"name": "relation"}), page.find("input", attrs={"name": "relative_id"})) == (
        None,
        None,
    )


def test_new_dialog_starts_with_sex_and_living_status_unknown():
    html = render_component(tag=TAG, context=NEW_PERSON)

    page = parse(html)
    assert page.find("input", attrs={"name": "sex", "checked": True})["value"] == "U"
    assert page.find("input", attrs={"name": "living_status", "checked": True})["value"] == "unknown"


def test_new_dialog_closes_on_cancel():
    html = render_component(tag=TAG, context=NEW_PERSON)

    assert parse(html).find("button", string="Abbrechen")["data-on:click"] == "el.closest('dialog').close()"
