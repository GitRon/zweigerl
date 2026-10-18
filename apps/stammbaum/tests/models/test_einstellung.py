import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError

from apps.stammbaum.models import Einstellung
from apps.stammbaum.tests.factories.einstellung import EinstellungFactory


def test_einstellung_str():
    assert str(Einstellung()) == "Einstellungen des Stammbaums"


@pytest.mark.django_db
def test_einstellung_refuses_a_second_row_on_save():
    with pytest.raises(ValidationError, match="Es gibt nur eine Zeile Einstellungen"):
        Einstellung(id=2).save()


@pytest.mark.django_db
def test_einstellung_refuses_a_second_row_in_the_database():
    with pytest.raises(IntegrityError, match="einstellung_nur_eine_zeile"):
        Einstellung.objects.bulk_create([Einstellung(id=2)])


@pytest.mark.django_db
def test_einstellung_protects_the_ausgangsperson_from_deletion():
    einstellung = EinstellungFactory()

    with pytest.raises(ProtectedError, match="protected foreign keys"):
        einstellung.ausgangsperson.delete()
