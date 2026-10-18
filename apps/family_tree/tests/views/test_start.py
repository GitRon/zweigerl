import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed


@pytest.mark.django_db
def test_start_view_renders_the_start_page(admin_client):
    response = admin_client.get(reverse("family_tree:start-view"))

    assert response.status_code == 200
    assertTemplateUsed(response, "family_tree/start.html")
