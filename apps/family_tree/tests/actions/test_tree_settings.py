import pytest

from apps.family_tree.actions.tree_settings import choose_home_person
from apps.family_tree.models import Person, TreeSettings
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.tree_settings import TreeSettingsFactory


@pytest.mark.django_db
def test_choose_home_person_creates_the_settings():
    lena = PersonFactory()

    tree_settings = choose_home_person(person_id=lena.pk)

    assert TreeSettings.objects.get().home_person == tree_settings.home_person == lena


@pytest.mark.django_db
def test_choose_home_person_replaces_the_one_chosen_before():
    TreeSettingsFactory()
    markus = PersonFactory()

    choose_home_person(person_id=markus.pk)

    assert list(TreeSettings.objects.values_list("home_person", flat=True)) == [markus.pk]


@pytest.mark.django_db
def test_choose_home_person_refuses_somebody_not_in_the_tree():
    lena = PersonFactory()

    with pytest.raises(Person.DoesNotExist, match="Person matching query does not exist"):
        choose_home_person(person_id=lena.pk + 1)
