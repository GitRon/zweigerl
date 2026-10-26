import pytest
from django.core.management import call_command

from apps.family_tree.readers.trees import home_person
from apps.family_tree.tests.factories.tree import TreeFactory


@pytest.mark.django_db
def test_huber_family_loads_with_its_home_person():
    """
    The fixture is for development and the browser run, never for a test's data - see
    docs/patterns/testing-data.md. This only proves it still loads against the current models and passes
    the database constraints, which a hand-edited JSON file otherwise finds out in the browser. "loaddata"
    does not call "clean()", so the rules held there are not checked - see docs/patterns/family.md.
    """
    call_command("loaddata", "huber_family", verbosity=0)

    assert home_person(tree_id=TreeFactory().pk) is not None
