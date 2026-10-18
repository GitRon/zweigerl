import pytest
from django.urls import reverse

from apps.family_tree.tests.factories.person import PersonFactory


@pytest.mark.django_db
def test_person_card_view_patches_the_card_of_the_person(admin_client):
    lena = PersonFactory(given_names="Lena", surname="Huber")

    response = admin_client.get(
        reverse("family_tree:person-card-view", kwargs={"pk": lena.pk}), headers={"Datastar-Request": "true"}
    )

    body = b"".join(response.streaming_content).decode()
    assert response.status_code == 200
    assert 'id="person-card"' in body and "Lena Huber" in body


@pytest.mark.django_db
def test_person_card_view_of_somebody_not_there_is_not_found(admin_client):
    response = admin_client.get(
        reverse("family_tree:person-card-view", kwargs={"pk": 404}), headers={"Datastar-Request": "true"}
    )

    assert response.status_code == 404
