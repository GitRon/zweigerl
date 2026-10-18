import datetime

import pytest

from apps.stammbaum.models import Angabe
from apps.stammbaum.readers.beleg import angaben, quellen
from apps.stammbaum.tests.factories.angabe import AngabeFactory
from apps.stammbaum.tests.factories.partnerschaft import PartnerschaftFactory
from apps.stammbaum.tests.factories.person import PersonFactory
from apps.stammbaum.tests.factories.quelle import QuelleFactory
from apps.stammbaum.tests.factories.zitat import ZitatFactory


@pytest.mark.django_db
def test_angaben_lists_a_persons_facts_in_date_order_undated_last():
    lena = PersonFactory()
    beruf = AngabeFactory(person=lena, als_wert=True)
    gestorben = AngabeFactory(person=lena, art=Angabe.Art.GESTORBEN, datum_1=datetime.date(2009, 11, 14))
    geboren = AngabeFactory(person=lena)
    AngabeFactory()
    AngabeFactory(person=None, partnerschaft=PartnerschaftFactory(person_a=lena), art=Angabe.Art.GEHEIRATET)

    assert list(angaben(person=lena)) == [geboren, gestorben, beruf]


@pytest.mark.django_db
def test_angaben_marks_belegt_without_zitat_as_unbelegt():
    lena = PersonFactory()
    ohne_zitat = AngabeFactory(person=lena)
    mit_zitat = ZitatFactory(angabe__person=lena, angabe__als_wert=True).angabe
    vermutet = AngabeFactory(
        person=lena, art=Angabe.Art.GETAUFT, verlaesslichkeit=Angabe.Verlaesslichkeit.WAHRSCHEINLICH
    )

    result = set(angaben(person=lena).values_list("pk", "unbelegt"))

    assert result == {(ohne_zitat.pk, True), (mit_zitat.pk, False), (vermutet.pk, False)}


@pytest.mark.django_db
def test_quellen_are_filed_with_the_person_or_cited_by_their_facts():
    lena = PersonFactory()
    abgelegt = QuelleFactory(titel="Geburtsurkunde", personen=[lena])
    zitiert = ZitatFactory(angabe__person=lena, quelle__titel="Studienunterlagen").quelle
    ZitatFactory(angabe__person=lena, angabe__als_wert=True, quelle=abgelegt)
    QuelleFactory(titel="Fremde Quelle")

    assert list(quellen(person=lena)) == [abgelegt, zitiert]


@pytest.mark.django_db
def test_quellen_include_those_of_the_persons_partnerships():
    lena, markus = PersonFactory.create_batch(2)
    paar = PartnerschaftFactory(person_a=markus, person_b=lena)
    heiratsurkunde = ZitatFactory(
        angabe__person=None, angabe__partnerschaft=paar, angabe__art=Angabe.Art.GEHEIRATET
    ).quelle

    assert list(quellen(person=lena)) == [heiratsurkunde]
