from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import PersonList, PersonListEntry
from apps.family_tree.tests.factories.person import PersonFactory

TAG = '<c-settings.home-person :person_list="person_list" :home_person="home_person" />'


def test_home_person_posts_the_choice():
    lena = PersonFactory.build(pk=1)
    everybody = PersonList(
        entries=[PersonListEntry(person=lena, name="Lena Huber", initials="LH", lifespan="—")], total=1
    )

    html = render_component(tag=TAG, context={"person_list": everybody, "home_person": lena})

    assert (
        parse(html).find("form")["data-on:submit"]
        == f"@post('{reverse('family_tree:home-person-view')}', {{contentType: 'form'}})"
    )


def test_home_person_selects_the_chosen_person():
    lena = PersonFactory.build(pk=1)
    markus = PersonFactory.build(pk=2)
    everybody = PersonList(
        entries=[
            PersonListEntry(person=markus, name="Markus Brandl", initials="MB", lifespan="1950-2020"),
            PersonListEntry(person=lena, name="Lena Huber", initials="LH", lifespan="—"),
        ],
        total=2,
    )

    html = render_component(tag=TAG, context={"person_list": everybody, "home_person": markus})

    assert parse(html).find("option", selected=True).get_text() == "Markus Brandl (1950-2020)"


def test_home_person_without_a_choice_asks_for_one():
    lena = PersonFactory.build(pk=1)
    everybody = PersonList(
        entries=[PersonListEntry(person=lena, name="Lena Huber", initials="LH", lifespan="—")], total=1
    )

    html = render_component(tag=TAG, context={"person_list": everybody, "home_person": None})

    assert parse(html).find("option", selected=True).get_text() == "Keine gewählt"


def test_home_person_in_an_empty_tree_invites_the_first_person():
    html = render_component(tag=TAG, context={"person_list": PersonList(entries=[], total=0), "home_person": None})

    assert "Jeder Baum fangt mit an Zweigerl an. Mit dir." in parse(html).get_text()
