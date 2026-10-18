import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from apps.family_tree.tests.factories.person import PersonFactory


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
