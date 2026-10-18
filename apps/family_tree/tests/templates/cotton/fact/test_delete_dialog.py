from dataclasses import replace

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import FactEntry
from apps.family_tree.tests.factories.fact import FactFactory

TAG = '<c-fact.delete-dialog :entry="entry" url="/persons/7/facts/11/delete/" />'
MARRIAGE = FactEntry(
    fact=FactFactory.build(pk=11),
    label="Geheiratet",
    text="3. Mai 1958",
    reliability=None,
    citations=[],
    undocumented=True,
    partner="Markus Gruber",
)


def test_delete_dialog_opens_itself_and_goes_away_when_closed():
    html = render_component(tag=TAG, context={"entry": MARRIAGE})

    dialog = parse(html).find(id="delete-fact-dialog")
    assert (dialog["data-init"], dialog["data-on:close"], dialog["data-on:keydown"]) == (
        "el.showModal()",
        "el.remove()",
        "evt.key == 'Escape' && evt.stopPropagation()",
    )


def test_delete_dialog_says_which_fact_goes():
    html = render_component(tag=TAG, context={"entry": MARRIAGE})

    assert "Geheiratet: 3. Mai 1958, mit Markus Gruber" in parse(html).find("dialog").get_text()


def test_delete_dialog_names_a_fact_without_text_by_its_label():
    html = render_component(tag=TAG, context={"entry": replace(MARRIAGE, text="", partner=None)})

    assert parse(html).find("p").get_text() == "Geheiratet"


def test_delete_dialog_posts_with_the_search_still_running():
    html = render_component(tag=TAG, context={"entry": MARRIAGE})

    form = parse(html).find("form")
    assert (form["data-on:submit"], form.find("input", attrs={"name": "search"})["data-attr:value"]) == (
        "@post('/persons/7/facts/11/delete/', {contentType: 'form'})",
        "$search",
    )
