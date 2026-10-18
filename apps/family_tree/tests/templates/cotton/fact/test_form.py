from dataclasses import replace

import pytest
from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.models import Fact
from apps.family_tree.readers.person import CitationChoice, FactForm, KindChoice, PersonListEntry
from apps.family_tree.tests.factories.fact import FactFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.source import SourceFactory

TAG = '<c-fact.form :form="form" />'
GERTI = PersonFactory.build(pk=7, given_names="Gertrud")
MARKUS = PersonListEntry(person=PersonFactory.build(pk=9), name="Markus Gruber", initials="MG", lifespan="1955 –")
REGISTER = SourceFactory.build(pk=21, title="Taufbuch Mariazell")
CERTIFICATE = SourceFactory.build(pk=22, title="Heiratsurkunde")
NEW = FactForm(
    person=GERTI,
    fact=None,
    kind="birth",
    fields="date",
    label="",
    value="",
    date="",
    partner_id=None,
    reliability="documented",
    kinds=[
        KindChoice(value="birth", label="Geboren", fields="date"),
        KindChoice(value="occupation", label="Beruf", fields="value"),
        KindChoice(value="marriage", label="Geheiratet", fields="couple"),
        KindChoice(value="custom", label="Eigene", fields="custom"),
    ],
    partners=[MARKUS],
    reliabilities=list(Fact.Reliability.choices),
    citations=[],
)
MARRIAGE = replace(
    NEW,
    fact=FactFactory.build(pk=11, kind="marriage"),
    kind="marriage",
    fields="couple",
    date="3. Mai 1958",
    partner_id=9,
    reliability="probable",
    citations=[
        CitationChoice(source=REGISTER, cited=False, page=""),
        CitationChoice(source=CERTIFICATE, cited=True, page="Nr. 1958/12"),
    ],
)


def test_form_for_a_new_fact_takes_the_place_of_the_button_and_posts_to_create():
    html = render_component(tag=TAG, context={"form": NEW})

    form = parse(html).find("form")
    assert (form["id"], form["data-signals"], form["data-on:submit"]) == (
        "fact-new",
        "{fact_fields_new: 'date'}",
        f"@post('{reverse('family_tree:create-fact-view', kwargs={'pk': 7})}', {{contentType: 'form'}})",
    )


def test_form_for_a_fact_takes_its_place_and_posts_the_change():
    html = render_component(tag=TAG, context={"form": MARRIAGE})

    form = parse(html).find("form")
    assert (form["id"], form["data-signals"], form["data-on:submit"]) == (
        "fact-11",
        "{fact_fields_11: 'couple'}",
        f"@post('{reverse('family_tree:change-fact-view', kwargs={'pk': 7, 'fact_pk': 11})}', {{contentType: 'form'}})",
    )


def test_form_is_filled_in_with_the_fact():
    html = render_component(tag=TAG, context={"form": MARRIAGE})

    form = parse(html).find("form")
    assert (
        form.find("select", attrs={"name": "kind"}).find("option", selected=True)["value"],
        form.find("select", attrs={"name": "partner"}).find("option", selected=True).get_text(),
        form.find("input", attrs={"name": "date"})["value"],
        form.find("input", attrs={"name": "reliability", "checked": True})["value"],
        form.find("input", attrs={"name": "search"})["data-attr:value"],
    ) == ("marriage", "Markus Gruber", "3. Mai 1958", "probable", "$search")


def test_form_switches_its_fields_with_the_kind():
    html = render_component(tag=TAG, context={"form": NEW})

    select = parse(html).find("select", attrs={"name": "kind"})
    assert (select["data-on:change"], [option["data-fields"] for option in select.find_all("option")]) == (
        "$fact_fields_new = el.selectedOptions[0].dataset.fields",
        ["date", "value", "couple", "custom"],
    )


@pytest.mark.parametrize(
    ("name", "shown"),
    [
        ("label", "$fact_fields_new == 'custom'"),
        ("partner", "$fact_fields_new == 'couple'"),
        ("value", "['value', 'custom'].includes($fact_fields_new)"),
        ("date", "['date', 'couple', 'custom'].includes($fact_fields_new)"),
    ],
)
def test_form_shows_a_field_only_for_the_kinds_that_carry_it(name, shown):
    html = render_component(tag=TAG, context={"form": NEW})

    assert parse(html).find(attrs={"name": name}).find_parent("label")["data-show"] == shown


def test_form_offers_every_source_of_the_person_with_its_place():
    html = render_component(tag=TAG, context={"form": MARRIAGE})

    form = parse(html).find("form")
    assert (
        [(box["value"], box.has_attr("checked")) for box in form.find_all("input", attrs={"name": "sources"})],
        form.find("input", attrs={"name": "page_22"})["value"],
    ) == ([("21", False), ("22", True)], "Nr. 1958/12")


def test_form_without_sources_says_where_they_come_from():
    html = render_component(tag=TAG, context={"form": NEW})

    assert "Leg sie unter „Quellen“ an." in parse(html).find("form").get_text()


def test_form_cancels_by_fetching_the_card_again():
    html = render_component(tag=TAG, context={"form": NEW})

    assert parse(html).find("button", string="Abbrechen")["data-on:click"] == (
        f"@get('{reverse('family_tree:person-view', kwargs={'pk': 7})}')"
    )


def test_form_for_a_fact_asks_before_removing_it():
    html = render_component(tag=TAG, context={"form": MARRIAGE})

    assert parse(html).find("button", string="Entfernen")["data-on:click"] == (
        f"@get('{reverse('family_tree:delete-fact-view', kwargs={'pk': 7, 'fact_pk': 11})}')"
    )


def test_form_for_a_new_fact_has_nothing_to_remove():
    html = render_component(tag=TAG, context={"form": NEW})

    assert parse(html).find("button", string="Entfernen") is None
