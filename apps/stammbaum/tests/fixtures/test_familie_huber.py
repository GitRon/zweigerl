import pytest
from django.core.management import call_command

from apps.stammbaum.readers.einstellung import ausgangsperson


@pytest.mark.django_db
def test_familie_huber_loads_with_its_ausgangsperson():
    """
    The fixture is for development and the browser run, never for a test's data - see
    docs/patterns/testing-data.md. This only proves it still loads against the current models and passes
    the database constraints, which a hand-edited JSON file otherwise finds out in the browser. "loaddata"
    does not call "clean()", so the rules held there are not checked - see docs/patterns/familie.md.
    """
    call_command("loaddata", "familie_huber", verbosity=0)

    assert ausgangsperson() is not None
