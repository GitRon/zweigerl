import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from apps.family_tree.tests.factories.person import PersonFactory


@pytest.mark.django_db
def test_start_view_renders_the_start_page(admin_client):
    response = admin_client.get(reverse("family_tree:start-view"))

    assert response.status_code == 200
    assertTemplateUsed(response, "family_tree/start.html")


@pytest.mark.django_db
def test_start_view_lists_everybody(admin_client):
    lena = PersonFactory(given_names="Lena")

    response = admin_client.get(reverse("family_tree:start-view"))

    assert response.context["person_list"].entries[0].person == lena
