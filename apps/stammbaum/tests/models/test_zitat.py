import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError

from apps.stammbaum.models import Zitat
from apps.stammbaum.tests.factories.angabe import AngabeFactory
from apps.stammbaum.tests.factories.quelle import QuelleFactory
from apps.stammbaum.tests.factories.zitat import ZitatFactory


def test_zitat_str_names_angabe_and_quelle():
    zitat = ZitatFactory.build(
        angabe=AngabeFactory.build(als_wert=True), quelle=QuelleFactory.build(titel="Volkszählung 1939")
    )

    assert str(zitat) == "Beruf: Uhrmacher - Volkszählung 1939"


@pytest.mark.django_db
def test_zitat_refuses_the_same_source_twice_on_save():
    zitat = ZitatFactory()

    with pytest.raises(ValidationError, match="Diese Angabe zitiert diese Quelle schon"):
        ZitatFactory(angabe=zitat.angabe, quelle=zitat.quelle, stelle="fol. 13")


@pytest.mark.django_db
def test_zitat_refuses_the_same_source_twice_in_the_database():
    zitat = ZitatFactory()

    with pytest.raises(IntegrityError, match=r"stammbaum_zitat\.angabe_id, stammbaum_zitat\.quelle_id"):
        Zitat.objects.bulk_create([Zitat(angabe=zitat.angabe, quelle=zitat.quelle)])


@pytest.mark.django_db
def test_zitat_keeps_a_cited_source_from_being_deleted():
    zitat = ZitatFactory()

    with pytest.raises(ProtectedError, match="protected foreign keys"):
        zitat.quelle.delete()
