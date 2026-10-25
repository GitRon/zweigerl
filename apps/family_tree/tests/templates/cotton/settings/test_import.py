from django.urls import reverse

from apps.common.tests.html import parse, render_component


def test_import_into_an_empty_tree_fetches_the_dialog():
    html = render_component(tag='<c-settings.import :tree_empty="tree_empty" />', context={"tree_empty": True})

    button = parse(html).find("button")
    assert button["data-on:click"] == f"@get('{reverse('family_tree:gedcom-import-dialog-view')}')"


def test_import_into_a_tree_with_people_is_disabled_and_says_why():
    html = render_component(tag='<c-settings.import :tree_empty="tree_empty" />', context={"tree_empty": False})

    page = parse(html)
    assert page.find("button").has_attr("disabled") is True
    assert "nur in einen leeren Stammbaum" in page.get_text()
