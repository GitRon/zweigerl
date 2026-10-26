from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.trees import OpenTree
from apps.family_tree.tests.factories.tree import TreeFactory

TAG = '<c-tree.switcher :open_tree="open_tree" />'
HUBER = TreeFactory.build(pk=3, name="Familie Huber")


def test_switcher_of_the_only_tree_names_it_and_offers_nothing_else():
    html = render_component(tag=TAG, context={"open_tree": OpenTree(tree=HUBER, others=[])})

    switcher = parse(html).find(id="tree-switcher")
    assert (switcher.get_text(strip=True), switcher.find("a")) == ("Familie Huber", None)


def test_switcher_leads_to_each_other_tree():
    berger = TreeFactory.build(pk=4, name="Familie Berger")

    html = render_component(tag=TAG, context={"open_tree": OpenTree(tree=HUBER, others=[berger])})

    switcher = parse(html).find(id="tree-switcher")
    link = switcher.find("a")
    assert (switcher.find("summary").get_text(" ", strip=True), link.get_text(strip=True), link["href"]) == (
        "Familie Huber wechseln",
        "Familie Berger",
        reverse("family_tree:tree-view", kwargs={"tree_pk": 4}),
    )
