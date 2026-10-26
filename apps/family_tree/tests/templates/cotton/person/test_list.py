from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import PersonList, PersonListEntry
from apps.family_tree.tests.factories.person import PersonFactory


def test_list_shows_each_person_with_name_and_lifespan():
    entry = PersonListEntry(person=PersonFactory.build(pk=7), name="Gerti Huber", initials="GH", lifespan="* 1958")

    html = render_component(
        tag='<c-person.list :person_list="person_list" />',
        context={"person_list": PersonList(entries=[entry], total=1)},
    )

    assert parse(html).find(id="person-list-7").get_text(" ", strip=True) == "GH Gerti Huber * 1958"


def test_list_counts_the_hits_of_a_search_against_everybody():
    entry = PersonListEntry(person=PersonFactory.build(pk=7), name="Gerti Huber", initials="GH", lifespan="")

    html = render_component(
        tag='<c-person.list :person_list="person_list" search="gerti" />',
        context={"person_list": PersonList(entries=[entry], total=15)},
    )

    assert parse(html).find(attrs={"aria-live": "polite"}).get_text(" ", strip=True) == "Treffer 1 von 15"


def test_list_says_when_nobody_matches_the_search():
    html = render_component(
        tag='<c-person.list :person_list="person_list" search="Brandl" />',
        context={"person_list": PersonList(entries=[], total=15)},
    )

    assert "Niemand passt zu „Brandl“." in parse(html).get_text()


def test_list_of_an_empty_tree_invites_the_first_person():
    html = render_component(
        tag='<c-person.list :person_list="person_list" />',
        context={"person_list": PersonList(entries=[], total=0)},
    )

    assert "Jeder Baum fangt mit an Zweigerl an. Mit dir." in parse(html).get_text()


def test_list_shows_the_portrait_in_the_frame():
    entry = PersonListEntry(
        person=PersonFactory.build(pk=7),
        name="Gerti Huber",
        initials="GH",
        lifespan="",
        portrait_url="/media/photos/5/original.jpg",
        portrait_alt="Am Hof",
    )

    html = render_component(
        tag='<c-person.list :person_list="person_list" />',
        context={"person_list": PersonList(entries=[entry], total=1)},
    )

    image = parse(html).find(id="person-list-7").find("img")
    assert (image["src"], image["alt"]) == ("/media/photos/5/original.jpg", "Am Hof")


def test_list_selects_a_person_opens_their_card_and_centres_them_in_the_tree():
    entry = PersonListEntry(person=PersonFactory.build(pk=7), name="Gerti Huber", initials="GH", lifespan="")

    html = render_component(
        tag='<c-person.list :person_list="person_list" />',
        context={"person_list": PersonList(entries=[entry], total=1)},
    )

    url = reverse("family_tree:person-view", kwargs={"pk": 7})
    button = parse(html).find(id="person-list-7").find("button")
    assert (button["data-on:click"], button["data-attr:aria-pressed"]) == (
        "$selection = 7; $focus = 7; "
        f"document.getElementById('person-card') ? @get('{url}') : location.assign('{url}')",
        "String($selection == 7)",
    )
