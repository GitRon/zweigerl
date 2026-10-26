import pytest
from django.urls import reverse

from apps.common.tests.html import parse, render_component


@pytest.mark.parametrize("tree_empty", [True, False])
def test_import_fetches_the_dialog_whether_the_tree_is_empty_or_not(tree_empty):
    html = render_component(tag='<c-settings.import :tree_empty="tree_empty" />', context={"tree_empty": tree_empty})

    button = parse(html).find("button")
    assert button["data-on:click"] == f"@get('{reverse('family_tree:gedcom-import-dialog-view')}')"


def test_import_into_a_tree_with_people_says_the_file_comes_on_top():
    html = render_component(tag='<c-settings.import :tree_empty="tree_empty" />', context={"tree_empty": False})

    assert "kommt zu den Personen dazu, die schon da sind" in " ".join(parse(html).get_text().split())
