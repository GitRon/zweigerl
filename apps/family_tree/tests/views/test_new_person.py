import json

import pytest
from django.urls import reverse

from apps.family_tree.models import ParentChild, Person
from apps.family_tree.tests.factories.parent_child import ParentChildFactory
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.tree import TreeFactory

DATASTAR = {"Datastar-Request": "true"}
FIELDS = {"given_names": "Rosa", "surname": "Huber", "sex": "F", "living_status": "living"}


def _events(response) -> str:
    return b"".join(response.streaming_content).decode()


@pytest.mark.django_db
def test_new_person_view_appends_the_dialog(admin_client):
    tree = TreeFactory()

    response = admin_client.get(reverse("family_tree:new-person-view", kwargs={"tree_pk": tree.pk}), headers=DATASTAR)

    body = _events(response)
    assert response.status_code == 200
    assert "selector body" in body and "mode append" in body and 'id="new-person-dialog"' in body


@pytest.mark.django_db
def test_create_person_view_opens_the_new_card(admin_client):
    tree = TreeFactory()

    response = admin_client.post(
        reverse("family_tree:create-person-view", kwargs={"tree_pk": tree.pk}), FIELDS, headers=DATASTAR
    )

    body = _events(response)
    rosa = Person.objects.get(tree=tree)
    assert reverse("family_tree:person-view", kwargs={"pk": rosa.pk}) in body
    assert admin_client.session["_toasts"] == [{"text": "Passt. Rosa Huber ist jetzt im Baum.", "style": "success"}]


@pytest.mark.django_db
def test_create_person_view_answers_a_refusal_with_its_reason(admin_client):
    tree = TreeFactory()

    response = admin_client.post(
        reverse("family_tree:create-person-view", kwargs={"tree_pk": tree.pk}), {**FIELDS, "sex": "Q"}, headers=DATASTAR
    )

    body = _events(response)
    assert Person.objects.exists() is False
    assert "Das Geschlecht ist männlich, weiblich, divers oder unbekannt." in body


@pytest.mark.django_db
def test_create_person_view_answers_a_tree_that_is_not_there(admin_client):
    tree = TreeFactory()

    response = admin_client.post(
        reverse("family_tree:create-person-view", kwargs={"tree_pk": tree.pk + 1}), FIELDS, headers=DATASTAR
    )

    assert "Diesen Stammbaum gibt es nicht mehr." in _events(response)


@pytest.mark.django_db
def test_new_relative_view_names_the_person_in_the_dialog(admin_client):
    lena = PersonFactory(given_names="Lena", surname="Huber")

    response = admin_client.get(reverse("family_tree:new-relative-view", kwargs={"pk": lena.pk}), headers=DATASTAR)

    body = _events(response)
    assert response.status_code == 200
    assert "Verwandte von Lena Huber hinzufügen" in body


@pytest.mark.django_db
def test_new_relative_view_of_somebody_not_there_is_not_found(admin_client):
    response = admin_client.get(reverse("family_tree:new-relative-view", kwargs={"pk": 404}), headers=DATASTAR)

    assert response.status_code == 404


@pytest.mark.django_db
def test_create_relative_view_opens_the_new_card(admin_client):
    lena = PersonFactory()

    response = admin_client.post(
        reverse("family_tree:create-relative-view", kwargs={"pk": lena.pk}),
        {**FIELDS, "relation": "child"},
        headers=DATASTAR,
    )

    body = _events(response)
    rosa = Person.objects.get(given_names="Rosa")
    assert reverse("family_tree:person-view", kwargs={"pk": rosa.pk}) in body
    assert list(ParentChild.objects.values_list("parent", "child")) == [(lena.pk, rosa.pk)]


@pytest.mark.django_db
def test_create_relative_view_refuses_somebody_not_in_the_tree(admin_client):
    response = admin_client.post(
        reverse("family_tree:create-relative-view", kwargs={"pk": 404}),
        {**FIELDS, "relation": "child"},
        headers=DATASTAR,
    )

    assert "Diese Person ist nicht mehr im Baum." in _events(response)


@pytest.mark.django_db
def test_create_relative_view_asks_for_the_relation(admin_client):
    lena = PersonFactory()

    response = admin_client.post(
        reverse("family_tree:create-relative-view", kwargs={"pk": lena.pk}), FIELDS, headers=DATASTAR
    )

    assert "Wähl aus, wie die beiden verwandt sind." in _events(response)


@pytest.mark.django_db
def test_create_relative_view_answers_a_refusal_with_its_reason(admin_client):
    lena = PersonFactory()
    ParentChildFactory.create_batch(2, child=lena)

    response = admin_client.post(
        reverse("family_tree:create-relative-view", kwargs={"pk": lena.pk}),
        {**FIELDS, "relation": "parent"},
        headers=DATASTAR,
    )

    assert "Dieses Kind hat schon zwei leibliche Eltern." in _events(response)


@pytest.mark.django_db
def test_relative_candidates_view_patches_whom_the_tree_offers(admin_client):
    lena = PersonFactory()
    maria = PersonFactory(given_names="Maria", surname="Gruber")

    response = admin_client.get(
        reverse("family_tree:relative-candidates-view", kwargs={"pk": lena.pk}),
        {"datastar": json.dumps({"relation": "parent", "relative_search": " gruber "})},
        headers=DATASTAR,
    )

    body = _events(response)
    assert response.status_code == 200
    assert 'id="relative-candidates"' in body and f'value="{maria.pk}"' in body


@pytest.mark.django_db
def test_create_relative_view_links_somebody_in_the_tree_and_opens_the_persons_card(admin_client):
    lena = PersonFactory(given_names="Lena", surname="Huber")
    josef = PersonFactory(given_names="Josef", surname="Huber")

    response = admin_client.post(
        reverse("family_tree:create-relative-view", kwargs={"pk": lena.pk}),
        {"relation": "parent", "relative_id": str(josef.pk), "partnership": ""},
        headers=DATASTAR,
    )

    assert reverse("family_tree:person-view", kwargs={"pk": lena.pk}) in _events(response)
    assert admin_client.session["_toasts"] == [
        {"text": "Passt. Josef Huber ist jetzt Elternteil von Lena Huber.", "style": "success"}
    ]


@pytest.mark.django_db
def test_create_relative_view_adds_a_child_of_the_couple(admin_client):
    couple = PartnershipFactory()

    response = admin_client.post(
        reverse("family_tree:create-relative-view", kwargs={"pk": couple.person_a.pk}),
        {**FIELDS, "relation": "child", "partnership": str(couple.pk), "pair_with_parent": "on"},
        headers=DATASTAR,
    )

    _events(response)
    rosa = Person.objects.get(given_names="Rosa")
    assert set(ParentChild.objects.filter(child=rosa).values_list("partnership", flat=True)) == {couple.pk}


@pytest.mark.django_db
def test_create_relative_view_refuses_a_couple_no_longer_there(admin_client):
    lena = PersonFactory()

    response = admin_client.post(
        reverse("family_tree:create-relative-view", kwargs={"pk": lena.pk}),
        {**FIELDS, "relation": "child", "partnership": "404"},
        headers=DATASTAR,
    )

    assert "Diese Partnerschaft gibt es nicht mehr." in _events(response)
