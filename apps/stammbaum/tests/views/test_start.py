import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed


@pytest.mark.django_db
def test_start_view_renders_the_start_page(client):
    response = client.get(reverse("stammbaum:start-view"))

    assert response.status_code == 200
    assertTemplateUsed(response, "stammbaum/start.html")
