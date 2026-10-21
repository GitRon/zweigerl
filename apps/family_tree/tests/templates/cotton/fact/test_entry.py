from dataclasses import replace

from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import FactEntry
from apps.family_tree.tests.factories.citation import CitationFactory
from apps.family_tree.tests.factories.fact import FactFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.source import SourceFactory

TAG = '<c-fact.entry :entry="entry" :person="person" />'
GERTI = PersonFactory.build(pk=7, given_names="Gertrud")
BIRTH = FactFactory.build(pk=11)
CITATION = CitationFactory.build(fact=BIRTH, source=SourceFactory.build(title="Taufbuch Mariazell"), page="fol. 12")
DOCUMENTED = FactEntry(
    fact=BIRTH, label="Geboren", text="12. März 1958", reliability=None, citations=[CITATION], undocumented=False
)


def test_entry_shows_the_beleg_of_a_documented_fact():
    html = render_component(tag=TAG, context={"entry": DOCUMENTED, "person": GERTI})

    text = parse(html).find(id="fact-11").get_text()
    assert "Beleg: Taufbuch Mariazell, fol. 12" in text and "unbelegt" not in text


def test_entry_marks_an_undocumented_fact():
    html = render_component(
        tag=TAG, context={"entry": replace(DOCUMENTED, citations=[], undocumented=True), "person": GERTI}
    )

    assert "unbelegt, Quelle fehlt" in parse(html).find(id="fact-11").get_text()


def test_entry_labels_a_probable_fact():
    html = render_component(
        tag=TAG, context={"entry": replace(DOCUMENTED, reliability="Wahrscheinlich", citations=[]), "person": GERTI}
    )

    assert "Wahrscheinlich" in parse(html).find(id="fact-11").get_text()


def test_entry_names_the_import_an_undocumented_fact_came_from_beside_its_mark():
    html = render_component(
        tag=TAG,
        context={"entry": replace(DOCUMENTED, citations=[], undocumented=True, origin="PAF Huber"), "person": GERTI},
    )

    text = parse(html).find(id="fact-11").get_text()
    assert "aus PAF Huber" in text and "unbelegt, Quelle fehlt" in text


def test_entry_names_no_import_for_a_fact_entered_here():
    html = render_component(tag=TAG, context={"entry": DOCUMENTED, "person": GERTI})

    assert "aus " not in parse(html).find(id="fact-11").get_text()


def test_entry_names_the_partner_of_a_couples_fact():
    html = render_component(
        tag=TAG, context={"entry": replace(DOCUMENTED, label="Geheiratet", partner="Markus Gruber"), "person": GERTI}
    )

    assert "mit Markus Gruber" in parse(html).find(id="fact-11").get_text()


def test_entry_asks_for_its_form_with_the_pencil():
    html = render_component(tag=TAG, context={"entry": DOCUMENTED, "person": GERTI})

    assert parse(html).find("button", attrs={"aria-label": "Geboren bearbeiten"})["data-on:click"] == (
        f"@get('{reverse('family_tree:edit-fact-view', kwargs={'pk': 7, 'fact_pk': 11})}')"
    )
