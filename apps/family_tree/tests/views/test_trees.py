import pytest
from django.urls import reverse

from apps.family_tree.models import Tree
from apps.family_tree.tests.factories.tree import TreeFactory

DATASTAR = {"Datastar-Request": "true"}


def _events(response) -> str:
    return b"".join(response.streaming_content).decode()


@pytest.mark.django_db
def test_create_tree_view_starts_the_tree_and_opens_it(admin_client):
    response = admin_client.post(reverse("family_tree:create-tree-view"), {"name": "Familie Berger"}, headers=DATASTAR)

    body = _events(response)
    berger = Tree.objects.get()
    assert reverse("family_tree:tree-view", kwargs={"tree_pk": berger.pk}) in body
    assert admin_client.session["_toasts"] == [{"text": "Passt. „Familie Berger“ ist angelegt.", "style": "success"}]


@pytest.mark.django_db
def test_create_tree_view_answers_a_refusal_with_its_reason(admin_client):
    TreeFactory(name="Familie Berger")

    response = admin_client.post(reverse("family_tree:create-tree-view"), {"name": "Familie Berger"}, headers=DATASTAR)

    assert "Einen Stammbaum mit diesem Namen gibt es schon." in _events(response)


@pytest.mark.django_db
def test_rename_tree_view_renames_the_tree_and_loads_its_settings_anew(admin_client):
    tree = TreeFactory(name="Stammbaum")

    response = admin_client.post(
        reverse("family_tree:rename-tree-view", kwargs={"tree_pk": tree.pk}),
        {"name": "Familie Huber"},
        headers=DATASTAR,
    )

    assert reverse("family_tree:tree-settings-view", kwargs={"tree_pk": tree.pk}) in _events(response)
    assert admin_client.session["_toasts"] == [
        {"text": "Passt. Der Stammbaum heißt jetzt „Familie Huber“.", "style": "success"}
    ]


@pytest.mark.django_db
def test_rename_tree_view_answers_a_refusal_with_its_reason(admin_client):
    tree = TreeFactory()

    response = admin_client.post(
        reverse("family_tree:rename-tree-view", kwargs={"tree_pk": tree.pk}), {"name": " "}, headers=DATASTAR
    )

    assert "Dieses Feld darf nicht leer sein." in _events(response)


@pytest.mark.django_db
def test_rename_tree_view_answers_a_tree_that_is_not_there(admin_client):
    tree = TreeFactory()

    response = admin_client.post(
        reverse("family_tree:rename-tree-view", kwargs={"tree_pk": tree.pk + 1}),
        {"name": "Familie Berger"},
        headers=DATASTAR,
    )

    assert "Diesen Stammbaum gibt es nicht mehr." in _events(response)
