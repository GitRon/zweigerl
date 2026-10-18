import datetime

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.family_tree.domain.dates import DateKind, Precision, UncertainDate
from apps.family_tree.models import Fact
from apps.family_tree.tests.factories.citation import CitationFactory
from apps.family_tree.tests.factories.fact import FactFactory
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.person import PersonFactory


def test_fact_str_shows_the_value():
    fact = FactFactory.build(as_value=True)

    assert str(fact) == "Beruf: Uhrmacher"


def test_fact_str_shows_the_date_and_an_own_label():
    fact = FactFactory.build(kind=Fact.Kind.CUSTOM, label="Firmung")

    assert str(fact) == "Firmung: 1931-03-12"


@pytest.mark.django_db
def test_fact_save_derives_the_sort_date():
    fact = FactFactory(between=True)

    assert Fact.objects.get(pk=fact.pk).sort_date == datetime.date(1825, 7, 1)


@pytest.mark.django_db
def test_fact_save_of_some_fields_keeps_the_sort_date_in_step():
    fact = FactFactory()
    fact.date_1 = datetime.date(1950, 6, 1)

    fact.save(update_fields=["date_1"])

    assert Fact.objects.get(pk=fact.pk).sort_date == datetime.date(1950, 6, 1)


@pytest.mark.django_db
def test_fact_save_leaves_a_fact_without_date_unsorted():
    fact = FactFactory(as_value=True)

    assert Fact.objects.get(pk=fact.pk).sort_date is None


def test_fact_date_is_the_structured_date():
    fact = FactFactory.build(between=True)

    assert fact.date == UncertainDate(
        kind=DateKind.BETWEEN,
        date_1=datetime.date(1820, 1, 1),
        date_2=datetime.date(1830, 1, 1),
        precision=Precision.YEAR,
    )


def test_fact_date_without_a_date_is_none():
    assert FactFactory.build(as_value=True).date is None


def test_fact_date_of_a_range_without_its_end_is_none():
    fact = FactFactory.build(between=True, date_2=None)

    assert fact.date is None


@pytest.mark.django_db
def test_fact_marked_documented_without_a_citation_is_undocumented():
    assert FactFactory(reliability=Fact.Reliability.DOCUMENTED).is_undocumented is True


@pytest.mark.django_db
def test_fact_with_a_citation_is_not_undocumented():
    assert CitationFactory().fact.is_undocumented is False


@pytest.mark.django_db
def test_fact_marked_probable_is_not_undocumented():
    assert FactFactory(reliability=Fact.Reliability.PROBABLE).is_undocumented is False


def test_fact_clean_derives_the_sort_date_for_the_form():
    fact = FactFactory.build()

    fact.clean()

    assert fact.sort_date == datetime.date(1931, 3, 12)


def test_fact_clean_refuses_a_marriage_on_an_unsaved_person():
    """
    The admin inline holds the person it hangs on as an unsaved object, and leaves the field out of the form
    - so the constraint is not checked there, and this is what turns a 500 into a message.
    """
    fact = FactFactory.build(person=PersonFactory.build(), kind=Fact.Kind.MARRIAGE)

    with pytest.raises(ValidationError, match="Heirat und Scheidung gehören zur Partnerschaft"):
        fact.clean()


def test_fact_clean_refuses_a_birth_on_a_partnership():
    fact = FactFactory.build(person=None, partnership=PartnershipFactory.build())

    with pytest.raises(ValidationError, match="gehört zu einer Person, nicht zur Partnerschaft"):
        fact.clean()


@pytest.mark.django_db
def test_fact_with_prefetched_citations_asks_nothing_more(django_assert_num_queries):
    fact = Fact.objects.prefetch_related("citations").get(pk=CitationFactory().fact.pk)

    with django_assert_num_queries(0):
        assert fact.is_undocumented is False


# Every constraint twice: through "save", which the mixin answers with the German message, and past it with
# "bulk_create", which only the database can refuse - see docs/patterns/testing-strategy.md.


@pytest.mark.django_db
def test_fact_refuses_a_person_and_a_partnership_at_once_on_save():
    with pytest.raises(ValidationError, match="entweder zu einer Person oder zu einer Partnerschaft"):
        FactFactory(partnership=PartnershipFactory())


@pytest.mark.django_db
def test_fact_refuses_a_person_and_a_partnership_at_once_in_the_database():
    with pytest.raises(IntegrityError, match="fact_one_owner"):
        Fact.objects.bulk_create(
            [
                FactFactory.build(
                    person=PersonFactory(),
                    partnership=PartnershipFactory(),
                    sort_date=datetime.date(1931, 3, 12),
                )
            ]
        )


@pytest.mark.django_db
def test_fact_refuses_an_unknown_kind_on_save():
    with pytest.raises(ValidationError, match="Diese Art von Angabe kennt Zweigerl nicht"):
        FactFactory(kind="made_up")


@pytest.mark.django_db
def test_fact_refuses_an_unknown_kind_in_the_database():
    with pytest.raises(IntegrityError, match="fact_kind_valid"):
        Fact.objects.bulk_create(
            [FactFactory.build(person=PersonFactory(), kind="made_up", sort_date=datetime.date(1931, 3, 12))]
        )


@pytest.mark.django_db
def test_fact_refuses_a_marriage_on_a_person_on_save():
    with pytest.raises(ValidationError, match="Heirat und Scheidung gehören zur Partnerschaft"):
        FactFactory(kind=Fact.Kind.MARRIAGE)


@pytest.mark.django_db
def test_fact_refuses_a_marriage_on_a_person_in_the_database():
    with pytest.raises(IntegrityError, match="fact_kind_matches_owner"):
        Fact.objects.bulk_create(
            [FactFactory.build(person=PersonFactory(), kind=Fact.Kind.MARRIAGE, sort_date=datetime.date(1931, 3, 12))]
        )


@pytest.mark.django_db
def test_fact_saves_a_marriage_on_a_partnership():
    fact = FactFactory(person=None, partnership=PartnershipFactory(), kind=Fact.Kind.MARRIAGE)

    assert Fact.objects.get().partnership == fact.partnership


@pytest.mark.django_db
def test_fact_refuses_a_date_kind_without_a_date_on_save():
    with pytest.raises(ValidationError, match="ist ein Datum und braucht eines"):
        FactFactory(date_kind="", date_1=None, precision="", value="1931")


@pytest.mark.django_db
def test_fact_refuses_a_date_kind_without_a_date_in_the_database():
    with pytest.raises(IntegrityError, match="fact_date_kind_has_date"):
        Fact.objects.bulk_create(
            [FactFactory.build(person=PersonFactory(), date_kind="", date_1=None, precision="", value="1931")]
        )


@pytest.mark.django_db
def test_fact_refuses_a_value_kind_without_a_value_on_save():
    with pytest.raises(ValidationError, match="braucht einen Wert, aber kein Datum"):
        FactFactory(as_value=True, value="")


@pytest.mark.django_db
def test_fact_refuses_a_value_kind_without_a_value_in_the_database():
    with pytest.raises(IntegrityError, match="fact_value_kind_has_value"):
        Fact.objects.bulk_create([FactFactory.build(person=PersonFactory(), as_value=True, value="")])


@pytest.mark.django_db
def test_fact_refuses_an_own_kind_without_a_label_on_save():
    with pytest.raises(ValidationError, match="Eine eigene Angabe braucht eine Bezeichnung"):
        FactFactory(kind=Fact.Kind.CUSTOM)


@pytest.mark.django_db
def test_fact_refuses_an_own_kind_without_a_label_in_the_database():
    with pytest.raises(IntegrityError, match="fact_custom_has_label"):
        Fact.objects.bulk_create(
            [FactFactory.build(person=PersonFactory(), kind=Fact.Kind.CUSTOM, sort_date=datetime.date(1931, 3, 12))]
        )


@pytest.mark.django_db
def test_fact_refuses_a_date_without_its_precision_on_save():
    with pytest.raises(ValidationError, match="Ein Datum braucht seine Art und seine Genauigkeit"):
        FactFactory(precision="")


@pytest.mark.django_db
def test_fact_refuses_a_date_without_its_precision_in_the_database():
    with pytest.raises(IntegrityError, match="fact_date_complete"):
        Fact.objects.bulk_create(
            [FactFactory.build(person=PersonFactory(), precision="", sort_date=datetime.date(1931, 3, 12))]
        )


@pytest.mark.django_db
def test_fact_refuses_a_range_ending_before_it_starts_on_save():
    with pytest.raises(ValidationError, match="Ein zweites Datum gibt es nur bei „zwischen“"):
        FactFactory(between=True, date_2=datetime.date(1810, 1, 1))


@pytest.mark.django_db
def test_fact_refuses_a_range_ending_before_it_starts_in_the_database():
    with pytest.raises(IntegrityError, match="fact_date_2_only_between"):
        Fact.objects.bulk_create(
            [
                FactFactory.build(
                    person=PersonFactory(),
                    between=True,
                    date_2=datetime.date(1810, 1, 1),
                    sort_date=datetime.date(1820, 1, 1),
                )
            ]
        )


@pytest.mark.django_db
def test_fact_refuses_a_second_date_on_an_exact_date_on_save():
    with pytest.raises(ValidationError, match="Ein zweites Datum gibt es nur bei „zwischen“"):
        FactFactory(date_2=datetime.date(1940, 1, 1))


@pytest.mark.django_db
def test_fact_refuses_a_date_without_its_sort_date_in_the_database():
    with pytest.raises(IntegrityError, match="fact_sort_date_with_date"):
        Fact.objects.bulk_create([FactFactory.build(person=PersonFactory())])


@pytest.mark.django_db
def test_fact_refuses_an_unknown_reliability_on_save():
    with pytest.raises(ValidationError, match="belegt, wahrscheinlich oder überliefert"):
        FactFactory(reliability="guessed")


@pytest.mark.django_db
def test_fact_refuses_an_unknown_reliability_in_the_database():
    with pytest.raises(IntegrityError, match="fact_reliability_valid"):
        Fact.objects.bulk_create(
            [FactFactory.build(person=PersonFactory(), reliability="guessed", sort_date=datetime.date(1931, 3, 12))]
        )
