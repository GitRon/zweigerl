from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.tests.factories.person import PersonFactory

TAG = '<c-source.new :person="person" :kinds="kinds" />'
KINDS = [("civil_registry", "Standesamt"), ("other", "Sonstiges")]


def test_new_posts_the_source_for_the_person():
    html = render_component(tag=TAG, context={"person": PersonFactory.build(pk=7), "kinds": KINDS})

    form = parse(html).find("form")
    url = reverse("family_tree:source-create-view", kwargs={"pk": 7})
    assert (form["data-on:submit"], form["enctype"]) == (
        f"@post('{url}', {{contentType: 'form'}})",
        "multipart/form-data",
    )


def test_new_offers_the_kinds_with_sonstiges_chosen():
    html = render_component(tag=TAG, context={"person": PersonFactory.build(pk=7), "kinds": KINDS})

    select = parse(html).find("select", attrs={"name": "kind"})
    assert (
        select.find("option", value="civil_registry").get_text(),
        select.find("option", selected=True)["value"],
    ) == ("Standesamt", "other")


def test_new_takes_title_zitat_and_files():
    html = render_component(tag=TAG, context={"person": PersonFactory.build(pk=7), "kinds": KINDS})

    form = parse(html).find("form")
    assert (
        form.find("input", attrs={"name": "title"}).has_attr("required"),
        form.find("textarea")["name"],
        form.find("input", type="file").has_attr("multiple"),
    ) == (True, "description", True)
