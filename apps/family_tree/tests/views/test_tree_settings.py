import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from apps.family_tree.models import TreeSettings
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.tree_settings import TreeSettingsFactory


@pytest.mark.django_db
def test_tree_settings_view_renders_the_settings_page(admin_client):
    response = admin_client.get(reverse("family_tree:tree-settings-view"))

    assert response.status_code == 200
    assertTemplateUsed(response, "family_tree/tree_settings.html")


@pytest.mark.django_db
def test_tree_settings_view_shows_the_home_person(admin_client):
    tree_settings = TreeSettingsFactory()

    response = admin_client.get(reverse("family_tree:tree-settings-view"))

    assert response.context["home_person"] == tree_settings.home_person


@pytest.mark.django_db
def test_home_person_view_saves_the_choice_and_confirms_it(admin_client):
    markus = PersonFactory(given_names="Markus", surname="Brandl")

    response = admin_client.post(
        reverse("family_tree:home-person-view"), {"home_person": markus.pk}, headers={"Datastar-Request": "true"}
    )

    body = b"".join(response.streaming_content).decode()
    assert TreeSettings.objects.get().home_person == markus
    assert "Passt. Markus Brandl ist jetzt die Ausgangsperson." in body


@pytest.mark.django_db
def test_home_person_view_patches_who_hangs_loose_now(admin_client):
    lena = PersonFactory(given_names="Lena", surname="Huber")
    markus = PersonFactory(given_names="Markus", surname="Brandl")
    TreeSettingsFactory(home_person=lena)

    response = admin_client.post(
        reverse("family_tree:home-person-view"), {"home_person": markus.pk}, headers={"Datastar-Request": "true"}
    )

    events = b"".join(response.streaming_content).decode().split("\n\n")
    assert "Lena Huber" in next(event for event in events if 'id="loose-people"' in event)


@pytest.mark.django_db
@pytest.mark.parametrize("home_person", ["", "kein-schlüssel", "999"])
def test_home_person_view_refuses_somebody_not_in_the_tree(admin_client, home_person):
    response = admin_client.post(
        reverse("family_tree:home-person-view"), {"home_person": home_person}, headers={"Datastar-Request": "true"}
    )

    body = b"".join(response.streaming_content).decode()
    assert TreeSettings.objects.exists() is False
    assert "Diese Person ist nicht mehr im Baum." in body
