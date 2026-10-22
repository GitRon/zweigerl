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
        "{fact_fields_new: 'date', fact_reliability_new: 'documented', fact_cited_new: 0}",
        f"@post('{reverse('family_tree:create-fact-view', kwargs={'pk': 7})}', {{contentType: 'form'}})",
    )


def test_form_for_a_fact_takes_its_place_and_posts_the_change():
    html = render_component(tag=TAG, context={"form": MARRIAGE})

    form = parse(html).find("form")
    assert (form["id"], form["data-signals"], form["data-on:submit"]) == (
        "fact-11",
        "{fact_fields_11: 'couple', fact_reliability_11: 'probable', fact_cited_11: 1}",
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
    assert (
        select["data-on:change"],
        select.find("option", attrs={"value": "marriage"})["data-fields"],
        select.find("option", attrs={"value": "custom"})["data-fields"],
    ) == ("$fact_fields_new = el.selectedOptions[0].dataset.fields", "couple", "custom")


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
        form.find("input", attrs={"name": "sources", "value": "21"}).has_attr("checked"),
        form.find("input", attrs={"name": "sources", "value": "22"}).has_attr("checked"),
        form.find("input", attrs={"name": "page_22"})["value"],
    ) == (False, True, "Nr. 1958/12")


def test_form_without_sources_says_where_they_come_from():
    html = render_component(tag=TAG, context={"form": NEW})

    assert "Leg sie unter „Quellen“ an." in parse(html).find("form").get_text()


def test_form_without_sources_leads_to_the_sources_tab():
    html = render_component(tag=TAG, context={"form": NEW})

    assert parse(html).find("button", string="Zu den Quellen")["data-on:click"] == "$tab = 'sources'"


def test_form_follows_the_reliability_and_the_ticked_sources():
    html = render_component(tag=TAG, context={"form": MARRIAGE})

    form = parse(html).find("form")
    assert (
        form.find("input", attrs={"name": "reliability"}).find_parent("fieldset")["data-on:change"],
        form.find("input", attrs={"name": "sources"}).find_parent("fieldset")["data-on:change"],
    ) == (
        "$fact_reliability_11 = evt.target.value",
        "$fact_cited_11 = el.querySelectorAll('input[name=sources]:checked').length",
    )


def test_form_says_that_belegt_needs_a_source_while_none_is_ticked():
    html = render_component(tag=TAG, context={"form": NEW})

    hint = parse(html).find(id="fact-new-documented-hint")
    assert (hint["data-show"], hint.get_text(" ", strip=True)) == (
        "$fact_reliability_new == 'documented' && $fact_cited_new == 0",
        "Belegt braucht eine Quelle – bis du eine zitierst, steht die Angabe als unbelegt da.",
    )


def test_form_with_sources_points_at_them_from_the_hint():
    html = render_component(tag=TAG, context={"form": MARRIAGE})

    assert "Wähl sie unter „Belege“." in parse(html).find(id="fact-11-documented-hint").get_text()


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
