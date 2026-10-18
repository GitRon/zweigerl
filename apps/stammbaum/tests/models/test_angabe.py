import datetime

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.stammbaum.domain.datum import DatumArt, Genauigkeit, UnscharfesDatum
from apps.stammbaum.models import Angabe
from apps.stammbaum.tests.factories.angabe import AngabeFactory
from apps.stammbaum.tests.factories.partnerschaft import PartnerschaftFactory
from apps.stammbaum.tests.factories.person import PersonFactory
from apps.stammbaum.tests.factories.zitat import ZitatFactory


def test_angabe_str_shows_the_value():
    angabe = AngabeFactory.build(als_wert=True)

    assert str(angabe) == "Beruf: Uhrmacher"


def test_angabe_str_shows_the_date_and_an_own_label():
    angabe = AngabeFactory.build(art=Angabe.Art.EIGENE, bezeichnung="Firmung")

    assert str(angabe) == "Firmung: 1931-03-12"


@pytest.mark.django_db
def test_angabe_save_derives_the_sort_date():
    angabe = AngabeFactory(zwischen=True)

    assert Angabe.objects.get(pk=angabe.pk).sortierdatum == datetime.date(1824, 12, 31)


@pytest.mark.django_db
def test_angabe_save_leaves_an_angabe_without_date_unsorted():
    angabe = AngabeFactory(als_wert=True)

    assert Angabe.objects.get(pk=angabe.pk).sortierdatum is None


def test_angabe_datum_is_the_structured_date():
    angabe = AngabeFactory.build(zwischen=True)

    assert angabe.datum == UnscharfesDatum(
        art=DatumArt.ZWISCHEN,
        datum_1=datetime.date(1820, 1, 1),
        datum_2=datetime.date(1830, 1, 1),
        genauigkeit=Genauigkeit.JAHR,
    )


def test_angabe_datum_without_a_date_is_none():
    assert AngabeFactory.build(als_wert=True).datum is None


def test_angabe_datum_of_a_range_without_its_end_is_none():
    angabe = AngabeFactory.build(zwischen=True, datum_2=None)

    assert angabe.datum is None


@pytest.mark.django_db
def test_angabe_marked_belegt_without_a_zitat_is_unbelegt():
    assert AngabeFactory(verlaesslichkeit=Angabe.Verlaesslichkeit.BELEGT).ist_unbelegt is True


@pytest.mark.django_db
def test_angabe_with_a_zitat_is_not_unbelegt():
    assert ZitatFactory().angabe.ist_unbelegt is False


@pytest.mark.django_db
def test_angabe_marked_wahrscheinlich_is_not_unbelegt():
    assert AngabeFactory(verlaesslichkeit=Angabe.Verlaesslichkeit.WAHRSCHEINLICH).ist_unbelegt is False


# Every constraint twice: through "save", which the mixin answers with the German message, and past it with
# "bulk_create", which only the database can refuse - see docs/patterns/testing-strategy.md.


@pytest.mark.django_db
def test_angabe_refuses_a_person_and_a_partnership_at_once_on_save():
    with pytest.raises(ValidationError, match="entweder zu einer Person oder zu einer Partnerschaft"):
        AngabeFactory(partnerschaft=PartnerschaftFactory())


@pytest.mark.django_db
def test_angabe_refuses_a_person_and_a_partnership_at_once_in_the_database():
    with pytest.raises(IntegrityError, match="angabe_genau_ein_bezug"):
        Angabe.objects.bulk_create(
            [
                AngabeFactory.build(
                    person=PersonFactory(),
                    partnerschaft=PartnerschaftFactory(),
                    sortierdatum=datetime.date(1931, 3, 12),
                )
            ]
        )


@pytest.mark.django_db
def test_angabe_refuses_an_unknown_kind_on_save():
    with pytest.raises(ValidationError, match="Diese Art von Angabe kennt Zweigerl nicht"):
        AngabeFactory(art="erfunden")


@pytest.mark.django_db
def test_angabe_refuses_an_unknown_kind_in_the_database():
    with pytest.raises(IntegrityError, match="angabe_art_gueltig"):
        Angabe.objects.bulk_create(
            [AngabeFactory.build(person=PersonFactory(), art="erfunden", sortierdatum=datetime.date(1931, 3, 12))]
        )


@pytest.mark.django_db
def test_angabe_refuses_a_marriage_on_a_person_on_save():
    with pytest.raises(ValidationError, match="Heirat und Scheidung gehören zur Partnerschaft"):
        AngabeFactory(art=Angabe.Art.GEHEIRATET)


@pytest.mark.django_db
def test_angabe_refuses_a_marriage_on_a_person_in_the_database():
    with pytest.raises(IntegrityError, match="angabe_art_passt_zum_bezug"):
        Angabe.objects.bulk_create(
            [
                AngabeFactory.build(
                    person=PersonFactory(), art=Angabe.Art.GEHEIRATET, sortierdatum=datetime.date(1931, 3, 12)
                )
            ]
        )


@pytest.mark.django_db
def test_angabe_saves_a_marriage_on_a_partnership():
    angabe = AngabeFactory(person=None, partnerschaft=PartnerschaftFactory(), art=Angabe.Art.GEHEIRATET)

    assert Angabe.objects.get().partnerschaft == angabe.partnerschaft


@pytest.mark.django_db
def test_angabe_refuses_a_date_kind_without_a_date_on_save():
    with pytest.raises(ValidationError, match="ist ein Datum und braucht eines"):
        AngabeFactory(datum_art="", datum_1=None, genauigkeit="", wert="1931")


@pytest.mark.django_db
def test_angabe_refuses_a_date_kind_without_a_date_in_the_database():
    with pytest.raises(IntegrityError, match="angabe_datumsart_hat_datum"):
        Angabe.objects.bulk_create(
            [AngabeFactory.build(person=PersonFactory(), datum_art="", datum_1=None, genauigkeit="", wert="1931")]
        )


@pytest.mark.django_db
def test_angabe_refuses_a_value_kind_without_a_value_on_save():
    with pytest.raises(ValidationError, match="braucht einen Wert, aber kein Datum"):
        AngabeFactory(als_wert=True, wert="")


@pytest.mark.django_db
def test_angabe_refuses_a_value_kind_without_a_value_in_the_database():
    with pytest.raises(IntegrityError, match="angabe_wertart_hat_wert"):
        Angabe.objects.bulk_create([AngabeFactory.build(person=PersonFactory(), als_wert=True, wert="")])


@pytest.mark.django_db
def test_angabe_refuses_an_own_kind_without_a_label_on_save():
    with pytest.raises(ValidationError, match="Eine eigene Angabe braucht eine Bezeichnung"):
        AngabeFactory(art=Angabe.Art.EIGENE)


@pytest.mark.django_db
def test_angabe_refuses_an_own_kind_without_a_label_in_the_database():
    with pytest.raises(IntegrityError, match="angabe_eigene_hat_bezeichnung"):
        Angabe.objects.bulk_create(
            [
                AngabeFactory.build(
                    person=PersonFactory(), art=Angabe.Art.EIGENE, sortierdatum=datetime.date(1931, 3, 12)
                )
            ]
        )


@pytest.mark.django_db
def test_angabe_refuses_a_date_without_its_precision_on_save():
    with pytest.raises(ValidationError, match="Ein Datum braucht seine Art und seine Genauigkeit"):
        AngabeFactory(genauigkeit="")


@pytest.mark.django_db
def test_angabe_refuses_a_date_without_its_precision_in_the_database():
    with pytest.raises(IntegrityError, match="angabe_datum_vollstaendig"):
        Angabe.objects.bulk_create(
            [AngabeFactory.build(person=PersonFactory(), genauigkeit="", sortierdatum=datetime.date(1931, 3, 12))]
        )


@pytest.mark.django_db
def test_angabe_refuses_a_range_ending_before_it_starts_on_save():
    with pytest.raises(ValidationError, match="Ein zweites Datum gibt es nur bei „zwischen“"):
        AngabeFactory(zwischen=True, datum_2=datetime.date(1810, 1, 1))


@pytest.mark.django_db
def test_angabe_refuses_a_range_ending_before_it_starts_in_the_database():
    with pytest.raises(IntegrityError, match="angabe_datum_bis_nur_bei_zwischen"):
        Angabe.objects.bulk_create(
            [
                AngabeFactory.build(
                    person=PersonFactory(),
                    zwischen=True,
                    datum_2=datetime.date(1810, 1, 1),
                    sortierdatum=datetime.date(1820, 1, 1),
                )
            ]
        )


@pytest.mark.django_db
def test_angabe_refuses_a_second_date_on_an_exact_date_on_save():
    with pytest.raises(ValidationError, match="Ein zweites Datum gibt es nur bei „zwischen“"):
        AngabeFactory(datum_2=datetime.date(1940, 1, 1))


@pytest.mark.django_db
def test_angabe_refuses_an_unknown_reliability_on_save():
    with pytest.raises(ValidationError, match="belegt, wahrscheinlich oder überliefert"):
        AngabeFactory(verlaesslichkeit="geraten")


@pytest.mark.django_db
def test_angabe_refuses_an_unknown_reliability_in_the_database():
    with pytest.raises(IntegrityError, match="angabe_verlaesslichkeit_gueltig"):
        Angabe.objects.bulk_create(
            [
                AngabeFactory.build(
                    person=PersonFactory(), verlaesslichkeit="geraten", sortierdatum=datetime.date(1931, 3, 12)
                )
            ]
        )
