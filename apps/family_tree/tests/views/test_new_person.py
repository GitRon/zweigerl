import pytest
from django.urls import reverse

from apps.family_tree.models import ParentChild, Person
from apps.family_tree.tests.factories.parent_child import ParentChildFactory
from apps.family_tree.tests.factories.person import PersonFactory

DATASTAR = {"Datastar-Request": "true"}
FIELDS = {"given_names": "Rosa", "surname": "Huber", "sex": "F", "living_status": "living"}


def _events(response) -> str:
    return b"".join(response.streaming_content).decode()


@pytest.mark.django_db
def test_new_person_view_appends_the_dialog(admin_client):
    response = admin_client.get(reverse("family_tree:new-person-view"), headers=DATASTAR)

    body = _events(response)
    assert response.status_code == 200
    assert "selector body" in body and "mode append" in body and 'id="new-person-dialog"' in body


@pytest.mark.django_db
def test_create_person_view_opens_the_new_card(admin_client):
    response = admin_client.post(reverse("family_tree:create-person-view"), FIELDS, headers=DATASTAR)

    body = _events(response)
    rosa = Person.objects.get()
    assert reverse("family_tree:person-view", kwargs={"pk": rosa.pk}) in body
    assert admin_client.session["_toasts"] == [{"text": "Passt. Rosa Huber ist jetzt im Baum.", "style": "success"}]


@pytest.mark.django_db
def test_create_person_view_answers_a_refusal_with_its_reason(admin_client):
    response = admin_client.post(reverse("family_tree:create-person-view"), {**FIELDS, "sex": "Q"}, headers=DATASTAR)

    body = _events(response)
    assert Person.objects.exists() is False
    assert "Das Geschlecht ist männlich, weiblich, divers oder unbekannt." in body


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
