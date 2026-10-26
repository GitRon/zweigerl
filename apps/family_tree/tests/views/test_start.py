import pytest
from django.urls import reverse
from pytest_django.asserts import assertRedirects, assertTemplateUsed

from apps.family_tree.domain.backup import BackupAge
from apps.family_tree.models import Tree
from apps.family_tree.readers.trees import OpenTree
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.tree import TreeFactory


def _tree_url(*, tree: Tree) -> str:
    return reverse("family_tree:tree-view", kwargs={"tree_pk": tree.pk})


@pytest.mark.django_db
def test_start_view_leads_to_the_first_tree(admin_client):
    TreeFactory(name="Familie Huber")
    auer = TreeFactory(name="Familie Auer")

    response = admin_client.get(reverse("family_tree:start-view"))

    assertRedirects(response, _tree_url(tree=auer))


@pytest.mark.django_db
def test_start_view_without_a_tree_asks_for_the_first_one(admin_client):
    response = admin_client.get(reverse("family_tree:start-view"))

    assert response.status_code == 200
    assertTemplateUsed(response, "family_tree/first_tree.html")


@pytest.mark.django_db
def test_tree_view_renders_the_page_of_the_tree(admin_client):
    tree = TreeFactory()

    response = admin_client.get(_tree_url(tree=tree))

    assert response.status_code == 200
    assertTemplateUsed(response, "family_tree/start.html")


@pytest.mark.django_db
def test_tree_view_refuses_a_tree_that_is_not_there(admin_client):
    tree = TreeFactory()

    response = admin_client.get(reverse("family_tree:tree-view", kwargs={"tree_pk": tree.pk + 1}))

    assert response.status_code == 404


@pytest.mark.django_db
def test_tree_view_names_the_open_tree_and_the_others(admin_client):
    huber = TreeFactory(name="Familie Huber")
    berger = TreeFactory(name="Familie Berger")

    response = admin_client.get(_tree_url(tree=huber))

    assert response.context["open_tree"] == OpenTree(tree=huber, others=[berger])


@pytest.mark.django_db
def test_tree_view_lists_everybody_of_the_tree(admin_client):
    lena = PersonFactory(given_names="Lena")
    PersonFactory(tree__name="Familie Berger")

    response = admin_client.get(_tree_url(tree=lena.tree))

    people = response.context["person_list"]
    assert (people.total, people.entries[0].person) == (1, lena)


@pytest.mark.django_db
def test_tree_view_draws_the_tree(admin_client):
    lena = PersonFactory(given_names="Lena")

    response = admin_client.get(_tree_url(tree=lena.tree))

    assert response.context["tree"].cards[0].entry.person == lena


@pytest.mark.django_db
def test_tree_view_opens_no_card(admin_client):
    response = admin_client.get(_tree_url(tree=TreeFactory()))

    assert (response.context["card"], response.context["selection"]) == (None, 0)


@pytest.mark.django_db
def test_tree_view_says_when_the_last_backup_was(admin_client):
    response = admin_client.get(_tree_url(tree=TreeFactory()))

    assert response.context["last_backup"] == BackupAge(text="noch nie", overdue=True)
