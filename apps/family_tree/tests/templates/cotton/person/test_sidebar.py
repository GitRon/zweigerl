from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import PersonList


def test_sidebar_asks_the_server_for_the_list_as_one_types():
    html = render_component(
        tag='<c-person.sidebar :person_list="person_list" />',
        context={"person_list": PersonList(entries=[], total=0)},
    )

    search_field = parse(html).find("input", attrs={"type": "search"})
    assert (search_field["data-bind"], search_field["data-on:input__debounce.300ms"]) == (
        "search",
        f"@get('{reverse('family_tree:person-search-view')}')",
    )


def test_sidebar_leads_to_the_settings():
    html = render_component(
        tag='<c-person.sidebar :person_list="person_list" />',
        context={"person_list": PersonList(entries=[], total=0)},
    )

    assert parse(html).find("a", string="Einstellungen")["href"] == reverse("family_tree:tree-settings-view")
