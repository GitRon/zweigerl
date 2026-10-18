"""
The login and the lockout are Django's and django-axes' own views; what is ours is the wiring - that every
page sits behind them, and that the lockout follows the settings in docs/patterns/data-storage.md.
"""

import pytest
from django.urls import reverse
from pytest_django.asserts import assertRedirects, assertTemplateUsed


@pytest.mark.django_db
def test_an_anonymous_visit_is_sent_to_the_login(client):
    response = client.get(reverse("stammbaum:start-view"))

    assertRedirects(response, f"{reverse('common:login-view')}?next=/")


@pytest.mark.django_db
def test_login_view_renders_without_a_login(client):
    response = client.get(reverse("common:login-view"))

    assert response.status_code == 200
    assertTemplateUsed(response, "common/login.html")


@pytest.mark.django_db
def test_login_view_lands_on_the_start_page(client, admin_user):
    response = client.post(reverse("common:login-view"), {"username": "admin", "password": "password"})

    assertRedirects(response, reverse("stammbaum:start-view"))


@pytest.mark.django_db
def test_login_view_shows_the_form_again_after_a_wrong_password(client, admin_user):
    response = client.post(reverse("common:login-view"), {"username": "admin", "password": "falsch"})

    assert response.status_code == 200
    assert response.context["form"].is_valid() is False


@pytest.mark.django_db
def test_login_view_locks_the_username_after_three_wrong_passwords(client, admin_user):
    login_url = reverse("common:login-view")
    client.post(login_url, {"username": "admin", "password": "falsch"})
    client.post(login_url, {"username": "admin", "password": "falsch"})
    client.post(login_url, {"username": "admin", "password": "falsch"})

    response = client.post(login_url, {"username": "admin", "password": "password"})

    assert response.status_code == 429
    assertTemplateUsed(response, "common/login_lockout.html")


@pytest.mark.django_db
def test_logout_view_ends_the_session(admin_client):
    response = admin_client.post(reverse("common:logout-view"))

    assertRedirects(response, reverse("common:login-view"))
