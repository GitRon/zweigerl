from dataclasses import replace

from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import FactEntry, PersonCard, PersonListEntry, RelativeGroup
from apps.family_tree.tests.factories.citation import CitationFactory
from apps.family_tree.tests.factories.fact import FactFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.source import SourceFactory

GERTI = PersonListEntry(person=PersonFactory.build(pk=7), name="Gerti Huber", initials="GH", lifespan="1958 –")
JOHANN = PersonListEntry(person=PersonFactory.build(pk=3), name="Johann Huber", initials="JH", lifespan="1931 – 2009")
BIRTH = FactFactory.build(pk=11)
CITATION = CitationFactory.build(fact=BIRTH, source=SourceFactory.build(title="Taufbuch Mariazell"), page="fol. 12")


CARD = PersonCard(entry=GERTI, relationship=None, facts=[], relatives=[], relative_count=0)
DOCUMENTED = FactEntry(
    fact=BIRTH, label="Geboren", text="12. März 1958", reliability=None, citations=[CITATION], undocumented=False
)
UNDOCUMENTED = replace(DOCUMENTED, citations=[], undocumented=True)
PROBABLE = replace(DOCUMENTED, reliability="Wahrscheinlich", citations=[])
PARENTS = RelativeGroup(title="Eltern", entries=[JOHANN])


def test_card_shows_name_lifespan_and_relationship():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": replace(CARD, relationship="Tante")})

    page = parse(html)
    assert page.find("h2").get_text() == "Gerti Huber"
    assert "1958 –" in page.get_text() and "Tante" in page.get_text()


def test_card_shows_while_the_person_is_selected():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": CARD})

    assert parse(html).find(id="person-card")["data-show"] == "$selection == 7"


def test_card_moves_the_address_back_to_the_start_page_when_closed():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": CARD})

    assert parse(html).find(id="person-card")["data-effect"] == (
        "$selection == 0 && location.pathname != '/' && history.pushState(null, '', '/')"
    )


def test_card_asks_for_a_new_relative():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": CARD})

    assert parse(html).find("button", string="Verwandte hinzufügen")["data-on:click"] == (
        f"@get('{reverse('family_tree:new-relative-view', kwargs={'pk': 7})}')"
    )


def test_card_closes_by_clearing_the_selection():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": CARD})

    assert parse(html).find("button", string="Schließen")["data-on:click"] == "$selection = 0"


def test_card_switches_tabs_with_their_counts():
    html = render_component(
        tag='<c-person.card :card="card" />',
        context={"card": replace(CARD, facts=[UNDOCUMENTED], relatives=[PARENTS], relative_count=1)},
    )

    page = parse(html)
    assert (
        " ".join(page.find(id="person-card-tab-facts").get_text().split()),
        page.find(id="person-card-tab-facts")["data-on:click"],
        " ".join(page.find(id="person-card-tab-relatives").get_text().split()),
        page.find(id="person-card-tab-relatives")["data-on:click"],
    ) == ("Angaben 1", "$tab = 'facts'", "Verwandte 1", "$tab = 'relatives'")


def test_card_offers_the_tabs_of_later_tickets_disabled():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": CARD})

    page = parse(html)
    assert (
        page.find("button", string="Fotos").has_attr("disabled"),
        page.find("button", string="Quellen").has_attr("disabled"),
        page.find("button", string="Notizen").has_attr("disabled"),
    ) == (True, True, True)


def test_card_shows_the_beleg_of_a_documented_fact():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": replace(CARD, facts=[DOCUMENTED])})

    text = parse(html).find(id="fact-11").get_text()
    assert "Beleg: Taufbuch Mariazell, fol. 12" in text and "unbelegt" not in text


def test_card_marks_an_undocumented_fact():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": replace(CARD, facts=[UNDOCUMENTED])})

    assert "unbelegt, Quelle fehlt" in parse(html).find(id="fact-11").get_text()


def test_card_labels_a_probable_fact():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": replace(CARD, facts=[PROBABLE])})

    assert "Wahrscheinlich" in parse(html).find(id="fact-11").get_text()


def test_card_without_facts_says_so():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": CARD})

    assert parse(html).find(id="person-card-facts").get_text().strip() == "Zu dieser Person steht noch nix da."


def test_card_opens_the_card_of_a_relative():
    html = render_component(
        tag='<c-person.card :card="card" />',
        context={"card": replace(CARD, relatives=[PARENTS], relative_count=1)},
    )

    relatives = parse(html).find(id="person-card-relatives")
    assert ("Eltern" in relatives.get_text(), relatives.find("button")["data-on:click"]) == (
        True,
        f"$selection = 3; @get('{reverse('family_tree:person-view', kwargs={'pk': 3})}')",
    )


def test_card_without_relatives_says_so():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": CARD})

    assert (
        parse(html).find(id="person-card-relatives").get_text().strip() == "Noch niemand mit dieser Person verbunden."
    )
