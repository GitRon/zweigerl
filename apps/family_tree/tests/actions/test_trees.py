import pytest
from django.core.exceptions import ValidationError

from apps.family_tree.actions.trees import choose_home_person, create_tree, rename_tree
from apps.family_tree.models import Person, Tree
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.tree import TreeFactory


@pytest.mark.django_db
def test_create_tree_starts_an_empty_tree_under_the_name():
    tree = create_tree(name="  Familie Berger ")

    assert list(Tree.objects.values_list("name", "home_person")) == [(tree.name, None)] == [("Familie Berger", None)]


@pytest.mark.django_db
def test_create_tree_refuses_a_name_already_taken():
    TreeFactory(name="Familie Berger")

    with pytest.raises(ValidationError, match="Einen Stammbaum mit diesem Namen gibt es schon"):
        create_tree(name="Familie Berger")


@pytest.mark.django_db
def test_create_tree_refuses_an_empty_name():
    with pytest.raises(ValidationError, match="Dieses Feld darf nicht leer sein"):
        create_tree(name=" ")


@pytest.mark.django_db
def test_rename_tree_gives_the_tree_the_new_name():
    tree = TreeFactory(name="Stammbaum")

    rename_tree(tree_id=tree.pk, name=" Familie Huber ")

    assert Tree.objects.get().name == "Familie Huber"


@pytest.mark.django_db
def test_rename_tree_refuses_a_name_another_tree_has():
    TreeFactory(name="Familie Berger")
    tree = TreeFactory(name="Familie Huber")

    with pytest.raises(ValidationError, match="Einen Stammbaum mit diesem Namen gibt es schon"):
        rename_tree(tree_id=tree.pk, name="Familie Berger")


@pytest.mark.django_db
def test_rename_tree_refuses_a_tree_that_is_not_there():
    tree = TreeFactory()

    with pytest.raises(Tree.DoesNotExist, match="Tree matching query does not exist"):
        rename_tree(tree_id=tree.pk + 1, name="Familie Berger")


@pytest.mark.django_db
def test_choose_home_person_makes_the_person_the_home_person_of_their_tree():
    lena = PersonFactory()

    tree = choose_home_person(tree_id=lena.tree_id, person_id=lena.pk)

    assert Tree.objects.get().home_person == tree.home_person == lena


@pytest.mark.django_db
def test_choose_home_person_replaces_the_one_chosen_before():
    markus = PersonFactory()
    tree = TreeFactory(home_person=PersonFactory())

    choose_home_person(tree_id=tree.pk, person_id=markus.pk)

    assert list(Tree.objects.values_list("home_person", flat=True)) == [markus.pk]


@pytest.mark.django_db
def test_choose_home_person_refuses_somebody_not_in_the_tree():
    lena = PersonFactory()

    with pytest.raises(Person.DoesNotExist, match="Person matching query does not exist"):
        choose_home_person(tree_id=lena.tree_id, person_id=lena.pk + 1)


@pytest.mark.django_db
def test_choose_home_person_refuses_somebody_of_another_tree():
    lena = PersonFactory()
    berger = TreeFactory(name="Familie Berger")

    with pytest.raises(Person.DoesNotExist, match="Person matching query does not exist"):
        choose_home_person(tree_id=berger.pk, person_id=lena.pk)
