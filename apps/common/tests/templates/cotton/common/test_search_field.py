from apps.common.tests.html import parse, render_component

TAG = '<c-common.search-field bind="search" label="Personen suchen" url="/persons/search/" data-on:keydown="false" />'


def test_search_field_asks_the_url_as_one_types():
    field = parse(render_component(tag=TAG, context={})).find("input")

    assert (
        field["aria-label"],
        field["data-bind"],
        field["data-on:input__debounce.300ms"],
        field["data-on:keydown"],
    ) == ("Personen suchen", "search", "@get('/persons/search/')", "false")


def test_search_field_cross_empties_the_search_while_there_is_one():
    cross = parse(render_component(tag=TAG, context={})).find("button", attrs={"aria-label": "Suche leeren"})

    assert (cross["data-show"], cross["data-on:click"]) == (
        "$search != ''",
        "$search = ''; @get('/persons/search/'); el.previousElementSibling.focus()",
    )
