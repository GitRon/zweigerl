import pytest
from django.urls import reverse

from apps.family_tree.models import ParentChild, Person
from apps.family_tree.tests.factories.parent_child import ParentChildFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.tree import TreeFactory

DATASTAR = {"Datastar-Request": "true"}


def _events(response) -> str:
    return b"".join(response.streaming_content).decode()


def _family() -> tuple[Person, Person, Person]:
    # Lena is the home person, Johann her father and Franz his - who hangs loose once Johann is deleted.
    lena = PersonFactory(given_names="Lena")
    johann = PersonFactory(given_names="Johann")
    franz = PersonFactory(given_names="Franz")
    ParentChildFactory(parent=johann, child=lena)
    ParentChildFactory(parent=franz, child=johann)
    TreeFactory(home_person=lena)
    return lena, johann, franz


@pytest.mark.django_db
def test_confirm_delete_person_view_appends_the_dialog(admin_client):
    johann = PersonFactory()

    response = admin_client.get(
        reverse("family_tree:confirm-delete-person-view", kwargs={"pk": johann.pk}), headers=DATASTAR
    )

    body = _events(response)
    assert response.status_code == 200
    assert "selector body" in body and "mode append" in body and 'id="delete-person-dialog"' in body


@pytest.mark.django_db
def test_confirm_delete_person_view_of_somebody_not_there_is_not_found(admin_client):
    response = admin_client.get(reverse("family_tree:confirm-delete-person-view", kwargs={"pk": 404}), headers=DATASTAR)

    assert response.status_code == 404


@pytest.mark.django_db
def test_delete_person_view_deletes_and_goes_back_to_the_page_of_the_tree(admin_client):
    _, johann, _ = _family()

    response = admin_client.post(
        reverse("family_tree:delete-person-view", kwargs={"pk": johann.pk}), {"loose_accepted": "1"}, headers=DATASTAR
    )

    body = _events(response)
    assert Person.objects.filter(pk=johann.pk).exists() is False
    assert reverse("family_tree:tree-view", kwargs={"tree_pk": johann.tree_id}) in body
    assert admin_client.session["_toasts"] == [{"text": "Passt. Johann Huber ist gelöscht.", "style": "success"}]


@pytest.mark.django_db
def test_delete_person_view_refuses_without_the_tick_for_those_cut_off(admin_client):
    _, johann, _ = _family()

    response = admin_client.post(
        reverse("family_tree:delete-person-view", kwargs={"pk": johann.pk}), {"loose_accepted": "2"}, headers=DATASTAR
    )

    body = _events(response)
    assert Person.objects.filter(pk=johann.pk).exists() is True
    assert "Ohne Johann Huber hängt 1 Person lose." in body


@pytest.mark.django_db
def test_delete_person_view_counts_several_cut_off_in_its_refusal(admin_client):
    _, johann, _ = _family()
    ParentChildFactory(parent=PersonFactory(), child=johann)

    response = admin_client.post(reverse("family_tree:delete-person-view", kwargs={"pk": johann.pk}), headers=DATASTAR)

    assert "Ohne Johann Huber hängen 2 Personen lose." in _events(response)


@pytest.mark.django_db
def test_delete_person_view_refuses_the_home_person(admin_client):
    lena, _, _ = _family()

    response = admin_client.post(reverse("family_tree:delete-person-view", kwargs={"pk": lena.pk}), headers=DATASTAR)

    body = _events(response)
    assert Person.objects.filter(pk=lena.pk).exists() is True
    assert "Das ist die Ausgangsperson." in body


@pytest.mark.django_db
def test_delete_person_view_of_somebody_not_there_says_so(admin_client):
    response = admin_client.post(reverse("family_tree:delete-person-view", kwargs={"pk": 404}), headers=DATASTAR)

    assert "Diese Person ist nicht mehr im Baum." in _events(response)


@pytest.mark.django_db
def test_confirm_unlink_view_appends_the_dialog(admin_client):
    link = ParentChildFactory()

    response = admin_client.get(
        reverse(
            "family_tree:confirm-unlink-view",
            kwargs={"pk": link.child_id, "relation": "parent", "relative_pk": link.parent_id},
        ),
        headers=DATASTAR,
    )

    body = _events(response)
    assert response.status_code == 200
    assert "selector body" in body and "mode append" in body and 'id="unlink-dialog"' in body


@pytest.mark.django_db
def test_confirm_unlink_view_without_such_a_link_is_not_found(admin_client):
    link = ParentChildFactory()

    response = admin_client.get(
        reverse(
            "family_tree:confirm-unlink-view",
            kwargs={"pk": link.child_id, "relation": "child", "relative_pk": link.parent_id},
        ),
        headers=DATASTAR,
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_unlink_view_removes_the_link_and_opens_the_card_again(admin_client):
    link = ParentChildFactory(parent__given_names="Johann", child__given_names="Lena")

    response = admin_client.post(
        reverse(
            "family_tree:unlink-view", kwargs={"pk": link.child_id, "relation": "parent", "relative_pk": link.parent_id}
        ),
        headers=DATASTAR,
    )

    body = _events(response)
    assert ParentChild.objects.exists() is False
    assert reverse("family_tree:person-view", kwargs={"pk": link.child_id}) in body
    assert admin_client.session["_toasts"] == [
        {"text": "Passt. Johann Huber und Lena Huber sind nicht mehr verbunden.", "style": "success"}
    ]


@pytest.mark.django_db
def test_unlink_view_of_a_link_gone_says_so(admin_client):
    link = ParentChildFactory()

    response = admin_client.post(
        reverse(
            "family_tree:unlink-view",
            kwargs={"pk": link.child_id, "relation": "partner", "relative_pk": link.parent_id},
        ),
        headers=DATASTAR,
    )

    assert "Diese Verbindung gibt es nicht mehr." in _events(response)
