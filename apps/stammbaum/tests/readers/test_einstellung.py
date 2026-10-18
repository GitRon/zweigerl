import pytest

from apps.stammbaum.readers.einstellung import ausgangsperson
from apps.stammbaum.tests.factories.einstellung import EinstellungFactory


@pytest.mark.django_db
def test_ausgangsperson_without_settings_is_none():
    assert ausgangsperson() is None


@pytest.mark.django_db
def test_ausgangsperson_is_the_chosen_person():
    einstellung = EinstellungFactory()

    assert ausgangsperson() == einstellung.ausgangsperson
