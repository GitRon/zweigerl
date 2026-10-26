from django.urls import reverse

from apps.common.tests.html import parse, render_component


def test_export_links_to_the_download():
    html = render_component(tag='<c-settings.export :tree_id="tree_id" />', context={"tree_id": 3})

    assert parse(html).find("a")["href"] == reverse("family_tree:gedcom-export-view", kwargs={"tree_pk": 3})
