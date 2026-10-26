"""
Requested by the literal path, not by "reverse": "/favicon.ico" is the address the browser guesses, so a route
that moved anywhere else would leave the tests green and the tab without its icon.
"""

import pytest
from django.templatetags.static import static
from pytest_django.asserts import assertRedirects


@pytest.mark.django_db
def test_favicon_view_points_an_anonymous_visit_at_the_icon(client):
    response = client.get("/favicon.ico")

    assertRedirects(response, static("brand/favicon-32.png"), fetch_redirect_response=False)


@pytest.mark.django_db
def test_favicon_view_points_a_logged_in_visit_at_the_icon(admin_client):
    response = admin_client.get("/favicon.ico")

    assertRedirects(response, static("brand/favicon-32.png"), fetch_redirect_response=False)
