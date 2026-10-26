import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from apps.family_tree.models import Person
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.tree import TreeFactory


@pytest.mark.django_db
def test_person_view_renders_the_start_page_with_the_card_open(admin_client):
    lena = PersonFactory(given_names="Lena", surname="Huber")

    response = admin_client.get(reverse("family_tree:person-view", kwargs={"pk": lena.pk}))

    assert (response.status_code, response.context["card"].entry.person, response.context["selection"]) == (
        200,
        lena,
        lena.pk,
    )
    assertTemplateUsed(response, "family_tree/start.html")


@pytest.mark.django_db
def test_person_view_opens_the_page_of_their_own_tree(admin_client):
    PersonFactory(given_names="Lena")
    markus = PersonFactory(given_names="Markus", tree__name="Familie Berger")

    response = admin_client.get(reverse("family_tree:person-view", kwargs={"pk": markus.pk}))

    people = response.context["person_list"]
    assert (response.context["open_tree"].tree, people.total, people.entries[0].person) == (
        markus.tree,
        1,
        markus,
    )


@pytest.mark.django_db
def test_person_view_patches_only_the_card_for_datastar(admin_client):
    lena = PersonFactory(given_names="Lena", surname="Huber")
    url = reverse("family_tree:person-view", kwargs={"pk": lena.pk})

    response = admin_client.get(url, headers={"Datastar-Request": "true"})

    body = b"".join(response.streaming_content).decode()
    assert response.status_code == 200
    assert 'id="person-card"' in body and f"history.pushState(null, '', \"{url}\")" in body


@pytest.mark.django_db
def test_person_view_of_somebody_not_there_is_not_found(admin_client):
    response = admin_client.get(reverse("family_tree:person-view", kwargs={"pk": 404}))

    assert response.status_code == 404


def _name_form(**changes) -> dict:
    return {
        "given_names": "Gertrud",
        "surname": "Huber",
        "call_name": "Gerti",
        "sex": Person.Sex.FEMALE,
        "living_status": Person.LivingStatus.LIVING,
        "death_year": "",
        "search": "",
        **changes,
    }


@pytest.mark.django_db
def test_person_name_view_saves_and_patches_card_list_and_tree(admin_client):
    gerti = PersonFactory(given_names="Gertrud", surname="Hubr")
    TreeFactory(home_person=gerti)

    response = admin_client.post(
        reverse("family_tree:person-name-view", kwargs={"pk": gerti.pk}),
        _name_form(),
        headers={"Datastar-Request": "true"},
    )

    body = b"".join(response.streaming_content).decode()
    gerti.refresh_from_db()
    assert (gerti.surname, gerti.call_name) == ("Huber", "Gerti")
    assert all(
        part in body
        for part in (
            'id="person-card"',
            '"editing":0',
            'id="person-list"',
            'id="loose-people"',
            f'id="tree-card-{gerti.pk}"',
            "Passt. Gerti Huber ist gespeichert.",
        )
    )


@pytest.mark.django_db
def test_person_name_view_patches_the_new_name_into_the_loose_twigs(admin_client):
    TreeFactory(home_person=PersonFactory())
    gerti = PersonFactory(given_names="Gertrud", surname="Hubr")

    response = admin_client.post(
        reverse("family_tree:person-name-view", kwargs={"pk": gerti.pk}),
        _name_form(),
        headers={"Datastar-Request": "true"},
    )

    events = b"".join(response.streaming_content).decode().split("\n\n")
    assert "Gerti Huber" in next(event for event in events if 'id="loose-people"' in event)


@pytest.mark.django_db
def test_person_name_view_keeps_the_search_running_in_the_list(admin_client):
    gerti = PersonFactory(given_names="Gertrud", surname="Huber")

    response = admin_client.post(
        reverse("family_tree:person-name-view", kwargs={"pk": gerti.pk}),
        _name_form(search="gerti"),
        headers={"Datastar-Request": "true"},
    )

    body = b"".join(response.streaming_content).decode()
    assert f'"matches":[{gerti.pk}]' in body


@pytest.mark.django_db
def test_person_name_view_does_not_patch_a_tree_card_the_tree_does_not_show(admin_client):
    TreeFactory(home_person=PersonFactory())
    stranger = PersonFactory(given_names="Fremd")

    response = admin_client.post(
        reverse("family_tree:person-name-view", kwargs={"pk": stranger.pk}),
        _name_form(),
        headers={"Datastar-Request": "true"},
    )

    body = b"".join(response.streaming_content).decode()
    assert f'id="tree-card-{stranger.pk}"' not in body


@pytest.mark.django_db
def test_person_name_view_refuses_a_death_year_that_is_no_number(admin_client):
    johann = PersonFactory(given_names="Johann")

    response = admin_client.post(
        reverse("family_tree:person-name-view", kwargs={"pk": johann.pk}),
        _name_form(living_status=Person.LivingStatus.DECEASED, death_year="um 2009"),
        headers={"Datastar-Request": "true"},
    )

    body = b"".join(response.streaming_content).decode()
    assert "Das Sterbejahr ist eine Jahreszahl, etwa 1931." in body


@pytest.mark.django_db
def test_person_name_view_answers_a_refusal_with_its_message(admin_client):
    johann = PersonFactory(given_names="Johann")

    response = admin_client.post(
        reverse("family_tree:person-name-view", kwargs={"pk": johann.pk}),
        _name_form(living_status=Person.LivingStatus.DECEASED, death_year="9999"),
        headers={"Datastar-Request": "true"},
    )

    body = b"".join(response.streaming_content).decode()
    assert "Das Sterbejahr ist eine Jahreszahl, höchstens die heurige." in body and 'id="person-card"' not in body


@pytest.mark.django_db
def test_person_name_view_of_somebody_not_there_says_so(admin_client):
    response = admin_client.post(
        reverse("family_tree:person-name-view", kwargs={"pk": 404}), _name_form(), headers={"Datastar-Request": "true"}
    )

    body = b"".join(response.streaming_content).decode()
    assert "Diese Person ist nicht mehr im Baum." in body
