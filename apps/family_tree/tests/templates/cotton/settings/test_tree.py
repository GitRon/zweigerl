from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.tests.factories.tree import TreeFactory

TAG = '<c-settings.tree :tree="tree" />'
HUBER = TreeFactory.build(pk=3, name="Familie Huber")


def test_tree_posts_the_new_name_of_the_tree():
    html = render_component(tag=TAG, context={"tree": HUBER})

    form = parse(html).find("button", string="Umbenennen").find_parent("form")
    assert (form["data-on:submit"], form.find("input", attrs={"name": "name"})["value"]) == (
        f"@post('{reverse('family_tree:rename-tree-view', kwargs={'tree_pk': 3})}', {{contentType: 'form'}})",
        "Familie Huber",
    )


def test_tree_starts_a_new_tree_with_the_name_entered():
    html = render_component(tag=TAG, context={"tree": HUBER})

    form = parse(html).find("button", string="Anlegen").find_parent("form")
    assert (form["data-on:submit"], form.find("input", attrs={"name": "name"}).has_attr("value")) == (
        f"@post('{reverse('family_tree:create-tree-view')}', {{contentType: 'form'}})",
        False,
    )
