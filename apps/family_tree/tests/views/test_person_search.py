import json

import pytest
from django.urls import reverse

from apps.family_tree.tests.factories.person import PersonFactory


@pytest.mark.django_db
def test_person_search_view_patches_the_list_with_the_hits(admin_client):
    PersonFactory(given_names="Lena", surname="Huber")
    PersonFactory(given_names="Markus", surname="Brandl")

    response = admin_client.get(
        reverse("family_tree:person-search-view"),
        {"datastar": json.dumps({"search": " brandl "})},
        headers={"Datastar-Request": "true"},
    )

    body = b"".join(response.streaming_content).decode()
    assert response.status_code == 200
    assert "Markus Brandl" in body and "Lena Huber" not in body


@pytest.mark.django_db
def test_person_search_view_hands_the_tree_the_hits(admin_client):
    PersonFactory(given_names="Lena", surname="Huber")
    markus = PersonFactory(given_names="Markus", surname="Brandl")

    response = admin_client.get(
        reverse("family_tree:person-search-view"),
        {"datastar": json.dumps({"search": "brandl"})},
        headers={"Datastar-Request": "true"},
    )

    body = b"".join(response.streaming_content).decode()
    assert f'data: signals {{"filtered":true,"matches":[{markus.pk}]}}' in body


@pytest.mark.django_db
def test_person_search_view_without_a_search_fades_nobody(admin_client):
    PersonFactory(given_names="Lena", surname="Huber")

    response = admin_client.get(
        reverse("family_tree:person-search-view"),
        {"datastar": json.dumps({"search": " "})},
        headers={"Datastar-Request": "true"},
    )

    body = b"".join(response.streaming_content).decode()
    assert '"filtered":false' in body
