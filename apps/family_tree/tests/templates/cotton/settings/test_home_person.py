import pytest
from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import PersonList, PersonListEntry
from apps.family_tree.tests.factories.person import PersonFactory

TAG = '<c-settings.home-person :tree_id="tree_id" :person_list="person_list" :home_person="home_person" />'


def test_home_person_posts_the_choice():
    lena = PersonFactory.build(pk=1)
    everybody = PersonList(
        entries=[PersonListEntry(person=lena, name="Lena Huber", initials="LH", lifespan="")], total=1
    )

    html = render_component(tag=TAG, context={"tree_id": 3, "person_list": everybody, "home_person": lena})

    assert (
        parse(html).find("form")["data-on:submit"]
        == f"@post('{reverse('family_tree:home-person-view', kwargs={'tree_pk': 3})}', {{contentType: 'form'}})"
    )


def test_home_person_selects_the_chosen_person():
    lena = PersonFactory.build(pk=1)
    markus = PersonFactory.build(pk=2)
    everybody = PersonList(
        entries=[
            PersonListEntry(person=markus, name="Markus Brandl", initials="MB", lifespan="1950-2020"),
            PersonListEntry(person=lena, name="Lena Huber", initials="LH", lifespan=""),
        ],
        total=2,
    )

    html = render_component(tag=TAG, context={"tree_id": 3, "person_list": everybody, "home_person": markus})

    assert parse(html).find("option", selected=True).get_text() == "Markus Brandl (1950-2020)"


def test_home_person_without_a_choice_asks_for_one():
    lena = PersonFactory.build(pk=1)
    everybody = PersonList(
        entries=[PersonListEntry(person=lena, name="Lena Huber", initials="LH", lifespan="")], total=1
    )

    html = render_component(tag=TAG, context={"tree_id": 3, "person_list": everybody, "home_person": None})

    assert parse(html).find("option", selected=True).get_text() == "Keine gewählt"


@pytest.mark.parametrize(
    ("lifespan", "text"), [("* 1950 † 2020", "Markus Brandl (* 1950 † 2020)"), ("", "Markus Brandl")]
)
def test_home_person_names_each_person_with_their_lifespan_if_there_is_one(lifespan, text):
    markus = PersonFactory.build(pk=2)
    everybody = PersonList(
        entries=[PersonListEntry(person=markus, name="Markus Brandl", initials="MB", lifespan=lifespan)], total=1
    )

    html = render_component(tag=TAG, context={"tree_id": 3, "person_list": everybody, "home_person": None})

    assert parse(html).find("option", attrs={"value": "2"}).get_text() == text


def test_home_person_in_an_empty_tree_invites_the_first_person():
    html = render_component(
        tag=TAG, context={"tree_id": 3, "person_list": PersonList(entries=[], total=0), "home_person": None}
    )

    assert "Jeder Baum fangt mit an Zweigerl an. Mit dir." in parse(html).get_text()
