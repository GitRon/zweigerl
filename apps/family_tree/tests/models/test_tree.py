import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError

from apps.family_tree.models import Tree
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.tree import TreeFactory


def test_tree_str():
    assert str(Tree(name="Familie Huber")) == "Familie Huber"


@pytest.mark.django_db
def test_tree_refuses_an_empty_name_on_save():
    with pytest.raises(ValidationError, match="Ein Stammbaum braucht einen Namen"):
        Tree(name="").save()


@pytest.mark.django_db
def test_tree_refuses_an_empty_name_in_the_database():
    with pytest.raises(IntegrityError, match="tree_has_name"):
        Tree.objects.bulk_create([Tree(name="")])


@pytest.mark.django_db
def test_tree_refuses_a_name_twice_on_save():
    TreeFactory(name="Familie Huber")

    with pytest.raises(ValidationError, match="Einen Stammbaum mit diesem Namen gibt es schon"):
        Tree(name="Familie Huber").save()


@pytest.mark.django_db
def test_tree_refuses_a_name_twice_in_the_database():
    TreeFactory(name="Familie Huber")

    with pytest.raises(IntegrityError, match=r"family_tree_tree\.name"):
        Tree.objects.bulk_create([Tree(name="Familie Huber")])


@pytest.mark.django_db
def test_tree_refuses_a_home_person_of_another_tree():
    lena = PersonFactory()
    berger = TreeFactory(name="Familie Berger")
    berger.home_person = lena

    with pytest.raises(ValidationError, match="Die Ausgangsperson gehört zu einem anderen Stammbaum"):
        berger.save()


@pytest.mark.django_db
def test_tree_protects_the_home_person_from_deletion():
    lena = TreeFactory(home_person=PersonFactory()).home_person

    with pytest.raises(ProtectedError, match="protected foreign keys"):
        lena.delete()


@pytest.mark.django_db
def test_tree_protects_itself_while_people_are_in_it():
    tree = PersonFactory().tree

    with pytest.raises(ProtectedError, match="protected foreign keys"):
        tree.delete()
