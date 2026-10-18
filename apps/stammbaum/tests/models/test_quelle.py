import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.stammbaum.models import Quelle
from apps.stammbaum.tests.factories.quelle import QuelleFactory


def test_quelle_str_is_its_title():
    assert str(QuelleFactory.build(titel="Geburtsurkunde")) == "Geburtsurkunde"


@pytest.mark.django_db
def test_quelle_refuses_a_missing_title_on_save():
    with pytest.raises(ValidationError, match="Eine Quelle braucht einen Titel"):
        QuelleFactory(titel="")


@pytest.mark.django_db
def test_quelle_refuses_a_missing_title_in_the_database():
    with pytest.raises(IntegrityError, match="quelle_hat_titel"):
        Quelle.objects.bulk_create([QuelleFactory.build(titel="")])


@pytest.mark.django_db
def test_quelle_refuses_an_unknown_kind_on_save():
    with pytest.raises(ValidationError, match="Diese Art von Quelle kennt Zweigerl nicht"):
        QuelleFactory(art="gerücht")


@pytest.mark.django_db
def test_quelle_refuses_an_unknown_kind_in_the_database():
    with pytest.raises(IntegrityError, match="quelle_art_gueltig"):
        Quelle.objects.bulk_create([QuelleFactory.build(art="gerücht")])
