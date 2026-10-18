import pytest
from django.db import IntegrityError
from django.db.models import ProtectedError

from apps.stammbaum.models import Einstellung
from apps.stammbaum.tests.factories.einstellung import EinstellungFactory


def test_einstellung_str():
    assert str(Einstellung()) == "Einstellungen des Stammbaums"


@pytest.mark.django_db
def test_einstellung_has_one_row_only():
    with pytest.raises(IntegrityError, match="CHECK constraint failed: einstellung_nur_eine_zeile"):
        Einstellung.objects.create(id=2)


@pytest.mark.django_db
def test_einstellung_protects_the_ausgangsperson_from_deletion():
    einstellung = EinstellungFactory()

    with pytest.raises(ProtectedError, match="protected foreign keys"):
        einstellung.ausgangsperson.delete()
