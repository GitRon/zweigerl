from dataclasses import replace

import pytest
from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import (
    FactEntry,
    PersonCard,
    PersonListEntry,
    PhotoEntry,
    PhotosTab,
    RelativeEntry,
    RelativeGroup,
    SourcesTab,
)
from apps.family_tree.tests.factories.citation import CitationFactory
from apps.family_tree.tests.factories.fact import FactFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.photo import PhotoFactory
from apps.family_tree.tests.factories.photo_person import PhotoPersonFactory
from apps.family_tree.tests.factories.source import SourceFactory

GERTI = PersonListEntry(
    person=PersonFactory.build(pk=7, given_names="Gertrud", call_name="Gerti", sex="F", living_status="living"),
    name="Gerti Huber",
    initials="GH",
    lifespan="* 1958",
)
JOHANN = PersonListEntry(person=PersonFactory.build(pk=3), name="Johann Huber", initials="JH", lifespan="* 1931 † 2009")
BIRTH = FactFactory.build(pk=11)
CITATION = CitationFactory.build(fact=BIRTH, source=SourceFactory.build(title="Taufbuch Mariazell"), page="fol. 12")


CARD = PersonCard(
    entry=GERTI,
    relationship=None,
    facts=[],
    relatives=[],
    relative_count=0,
    sources_tab=SourcesTab(person=GERTI.person, sources=[], kinds=[]),
    photos_tab=PhotosTab(person=GERTI.person, photos=[]),
    death_recorded=False,
)
DOCUMENTED = FactEntry(
    fact=BIRTH, label="Geboren", text="12. März 1958", reliability=None, citations=[CITATION], undocumented=False
)
PARENTS = RelativeGroup(title="Eltern", relation="parent", entries=[RelativeEntry(entry=JOHANN, unlinkable=True)])
SIBLINGS = RelativeGroup(
    title="Geschwister", relation="sibling", entries=[RelativeEntry(entry=JOHANN, unlinkable=False)]
)


def test_card_shows_name_lifespan_and_relationship():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": replace(CARD, relationship="Tante")})

    page = parse(html)
    assert page.find("h2").get_text() == "Gerti Huber"
    assert "* 1958" in page.get_text() and "Tante" in page.get_text()


def test_card_names_the_import_the_person_came_from():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": replace(CARD, origin="PAF Huber")})

    assert "Herkunft: PAF Huber" in parse(html).get_text()


def test_card_names_no_import_for_somebody_entered_here():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": CARD})

    assert "Herkunft" not in parse(html).get_text()


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

    assert parse(html).find("button", string="Schließen")["data-on:click"] == "$selection = 0; $editing = 0"


def test_card_switches_tabs_with_their_counts():
    html = render_component(
        tag='<c-person.card :card="card" />',
        context={"card": replace(CARD, facts=[DOCUMENTED], relatives=[PARENTS], relative_count=1)},
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

    assert parse(html).find("button", string="Notizen").has_attr("disabled") is True


def test_card_shows_the_portrait_in_its_head():
    entry = replace(GERTI, portrait_url="/media/photos/5/original.jpg", portrait_alt="Am Hof, 1975")

    html = render_component(tag='<c-person.card :card="card" />', context={"card": replace(CARD, entry=entry)})

    image = parse(html).find(id="person-card-portrait").find("img")
    assert (image["src"], image["alt"]) == ("/media/photos/5/original.jpg", "Am Hof, 1975")


def test_card_lists_the_photos_in_their_tab():
    photo = PhotoEntry(
        link=PhotoPersonFactory.build(photo=PhotoFactory.build(pk=5, description="Am Hof"), person=GERTI.person),
        url="/media/photos/5/original.jpg",
        alt="Am Hof",
        date="",
    )

    html = render_component(
        tag='<c-person.card :card="card" />',
        context={"card": replace(CARD, photos_tab=PhotosTab(person=GERTI.person, photos=[photo]))},
    )

    page = parse(html)
    assert (
        " ".join(page.find(id="person-card-tab-photos").get_text().split()),
        page.find(id="person-card-tab-photos")["data-on:click"],
        page.find(id="person-card-photos").find(id="photo-5") is not None,
    ) == ("Fotos 1", "$tab = 'photos'", True)


@pytest.mark.django_db
def test_card_lists_the_sources_in_their_tab():
    source = SourceFactory(title="Taufbuch Mariazell")

    html = render_component(
        tag='<c-person.card :card="card" />',
        context={"card": replace(CARD, sources_tab=SourcesTab(person=GERTI.person, sources=[source], kinds=[]))},
    )

    page = parse(html)
    assert (
        " ".join(page.find(id="person-card-tab-sources").get_text().split()),
        page.find(id="person-card-tab-sources")["data-on:click"],
        "Taufbuch Mariazell" in page.find(id="person-card-sources").get_text(),
    ) == ("Quellen 1", "$tab = 'sources'", True)


def test_card_lists_each_fact_as_its_entry():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": replace(CARD, facts=[DOCUMENTED])})

    assert "12. März 1958" in parse(html).find(id="fact-11").get_text()


def test_card_without_facts_says_so():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": CARD})

    assert "Zu dieser Person steht noch nix da." in parse(html).find(id="person-card-facts").get_text()


def test_card_asks_for_the_form_of_a_new_fact():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": CARD})

    assert parse(html).find(id="fact-new").find("button", string="Angabe hinzufügen")["data-on:click"] == (
        f"@get('{reverse('family_tree:new-fact-view', kwargs={'pk': 7})}')"
    )


def test_card_opens_the_card_of_a_relative():
    html = render_component(
        tag='<c-person.card :card="card" />',
        context={"card": replace(CARD, relatives=[PARENTS], relative_count=1)},
    )

    relatives = parse(html).find(id="person-card-relatives")
    assert ("Eltern" in relatives.get_text(), relatives.find("button")["data-on:click"]) == (
        True,
        f"$selection = 3; $focus = 3; @get('{reverse('family_tree:person-view', kwargs={'pk': 3})}')",
    )


def test_card_without_relatives_says_so():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": CARD})

    assert (
        parse(html).find(id="person-card-relatives").get_text().strip() == "Noch niemand mit dieser Person verbunden."
    )


def test_card_opens_the_form_for_name_and_status_with_the_pencil():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": CARD})

    assert parse(html).find("button", attrs={"aria-label": "Name & Status bearbeiten"})["data-on:click"] == (
        "$editing = 7; $status = 'living'"
    )


def test_card_form_posts_name_and_status_filled_in():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": CARD})

    form = parse(html).find(id="person-card-name")
    assert (
        form["data-show"],
        form["data-on:submit"],
        form.find("input", attrs={"name": "given_names"})["value"],
        form.find("input", attrs={"name": "call_name"})["value"],
        form.find("select", attrs={"name": "sex"}).find("option", selected=True)["value"],
        form.find("select", attrs={"name": "living_status"}).find("option", selected=True)["value"],
        form.find("input", attrs={"name": "search"})["data-attr:value"],
    ) == (
        "$editing == 7",
        f"@post('{reverse('family_tree:person-name-view', kwargs={'pk': 7})}', {{contentType: 'form'}})",
        "Gertrud",
        "Gerti",
        "F",
        "living",
        "$search",
    )


def test_card_form_asks_for_the_death_year_once_deceased_is_chosen():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": CARD})

    year = parse(html).find("input", attrs={"name": "death_year"})
    assert year.find_parent("label")["data-show"] == "$status == 'deceased'"


def test_card_form_does_not_ask_for_a_death_year_already_recorded():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": replace(CARD, death_recorded=True)})

    assert parse(html).find("input", attrs={"name": "death_year"}) is None


def test_card_form_cancels_by_closing_it():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": CARD})

    cancel = parse(html).find("button", string="Abbrechen")
    assert (cancel["type"], cancel["data-on:click"]) == ("reset", "$editing = 0")


def test_card_asks_before_unlinking_a_relative():
    html = render_component(
        tag='<c-person.card :card="card" />',
        context={"card": replace(CARD, relatives=[PARENTS], relative_count=1)},
    )

    button = parse(html).find("button", attrs={"aria-label": "Verbindung zu Johann Huber lösen"})
    url = reverse("family_tree:confirm-unlink-view", kwargs={"pk": 7, "relation": "parent", "relative_pk": 3})
    assert button["data-on:click"] == f"@get('{url}')"


def test_card_offers_no_unlinking_of_a_sibling_through_a_parent():
    html = render_component(
        tag='<c-person.card :card="card" />',
        context={"card": replace(CARD, relatives=[SIBLINGS], relative_count=1)},
    )

    assert parse(html).find("button", attrs={"aria-label": "Verbindung zu Johann Huber lösen"}) is None


def test_card_asks_before_deleting_the_person():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": CARD})

    assert parse(html).find("button", string="Löschen")["data-on:click"] == (
        f"@get('{reverse('family_tree:confirm-delete-person-view', kwargs={'pk': 7})}')"
    )


def test_card_centres_the_person_in_the_tree_when_chosen_from_outside_it():
    html = render_component(tag='<c-person.card :card="card" />', context={"card": CARD})

    head = parse(html).find("h2").find_parent(attrs={"data-show": "$editing != 7"})
    assert head["data-effect"] == (
        "$focus == 7 && ($focus = 0, requestAnimationFrame(() => document.getElementById('tree-card-7')"
        "?.scrollIntoView({block: 'center', inline: 'center'})))"
    )
