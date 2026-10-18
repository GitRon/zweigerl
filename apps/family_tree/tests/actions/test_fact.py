import datetime

import pytest
from django.core.exceptions import ValidationError

from apps.family_tree.actions.fact import change_fact, create_fact, delete_fact
from apps.family_tree.models import Citation, Fact, Person, Source
from apps.family_tree.tests.factories.citation import CitationFactory
from apps.family_tree.tests.factories.fact import FactFactory
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.source import SourceFactory

FIELDS = {
    "kind": Fact.Kind.BIRTH,
    "label": "",
    "value": "",
    "date": "12. März 1958",
    "partner_id": None,
    "reliability": Fact.Reliability.DOCUMENTED,
    "citations": {},
}


@pytest.mark.django_db
def test_create_fact_saves_a_date_read_from_german():
    lena = PersonFactory(given_names="Lena")

    fact = create_fact(person_id=lena.pk, **{**FIELDS, "date": "um 1931"})

    assert Fact.objects.values_list("person", "kind", "date_kind", "date_1", "precision").get(pk=fact.pk) == (
        lena.pk,
        "birth",
        "about",
        datetime.date(1931, 1, 1),
        "year",
    )


@pytest.mark.django_db
def test_create_fact_saves_a_value_without_surrounding_spaces():
    lena = PersonFactory(given_names="Lena")

    fact = create_fact(person_id=lena.pk, **{**FIELDS, "kind": Fact.Kind.OCCUPATION, "value": " Uhrmacherin "})

    assert Fact.objects.values_list("value", "date_1").get(pk=fact.pk) == ("Uhrmacherin", None)


@pytest.mark.django_db
def test_create_fact_drops_what_the_kind_does_not_carry():
    lena = PersonFactory(given_names="Lena")

    fact = create_fact(person_id=lena.pk, **{**FIELDS, "label": "Firmung", "value": "Mariazell"})

    assert Fact.objects.values_list("label", "value").get(pk=fact.pk) == ("", "")


@pytest.mark.django_db
def test_create_fact_saves_a_custom_fact_with_label_value_and_date():
    lena = PersonFactory(given_names="Lena")

    fact = create_fact(
        person_id=lena.pk,
        **{**FIELDS, "kind": Fact.Kind.CUSTOM, "label": "Firmung", "value": "Mariazell", "date": "1970"},
    )

    assert Fact.objects.values_list("label", "value", "date_1").get(pk=fact.pk) == (
        "Firmung",
        "Mariazell",
        datetime.date(1970, 1, 1),
    )


@pytest.mark.django_db
def test_create_fact_puts_a_marriage_on_the_partnership():
    partnership = PartnershipFactory()

    fact = create_fact(
        person_id=partnership.person_b.pk,
        **{**FIELDS, "kind": Fact.Kind.MARRIAGE, "partner_id": partnership.person_a.pk},
    )

    assert Fact.objects.values_list("person", "partnership").get(pk=fact.pk) == (None, partnership.pk)


@pytest.mark.django_db
def test_create_fact_refuses_a_marriage_with_somebody_who_is_no_partner():
    lena = PersonFactory(given_names="Lena")
    stranger = PersonFactory(given_names="Fremd")

    with pytest.raises(ValidationError, match="Wähl aus, wer der Partner ist"):
        create_fact(person_id=lena.pk, **{**FIELDS, "kind": Fact.Kind.MARRIAGE, "partner_id": stranger.pk})


@pytest.mark.django_db
def test_create_fact_cites_the_chosen_sources_with_their_place():
    lena = PersonFactory(given_names="Lena")
    source = SourceFactory(people=[lena])

    fact = create_fact(person_id=lena.pk, **{**FIELDS, "citations": {source.pk: " fol. 12 "}})

    assert list(Citation.objects.filter(fact=fact).values_list("source", "page")) == [(source.pk, "fol. 12")]


@pytest.mark.django_db
def test_create_fact_refuses_a_source_that_is_gone():
    lena = PersonFactory(given_names="Lena")

    with pytest.raises(ValidationError, match="Eine der Quellen ist nicht mehr da"):
        create_fact(person_id=lena.pk, **{**FIELDS, "citations": {404: ""}})

    assert Fact.objects.exists() is False


@pytest.mark.django_db
def test_create_fact_refuses_a_date_it_cannot_read():
    lena = PersonFactory(given_names="Lena")

    with pytest.raises(ValidationError, match="kein Datum, das Zweigerl lesen kann"):
        create_fact(person_id=lena.pk, **{**FIELDS, "date": "irgendwann"})


@pytest.mark.django_db
def test_create_fact_refuses_a_date_kind_without_a_date():
    lena = PersonFactory(given_names="Lena")

    with pytest.raises(ValidationError, match="braucht eines"):
        create_fact(person_id=lena.pk, **{**FIELDS, "date": " "})


@pytest.mark.django_db
def test_create_fact_refuses_a_value_longer_than_its_field():
    lena = PersonFactory(given_names="Lena")

    with pytest.raises(ValidationError, match="höchstens 300 Zeichen"):
        create_fact(person_id=lena.pk, **{**FIELDS, "kind": Fact.Kind.OCCUPATION, "value": "x" * 301})


@pytest.mark.django_db
def test_create_fact_for_somebody_not_there():
    with pytest.raises(Person.DoesNotExist):
        create_fact(person_id=404, **FIELDS)


@pytest.mark.django_db
def test_change_fact_saves_the_new_date_and_reliability():
    birth = FactFactory()

    change_fact(
        person_id=birth.person.pk,
        fact_id=birth.pk,
        **{**FIELDS, "date": "zwischen 1820 und 1825", "reliability": Fact.Reliability.HANDED_DOWN},
    )

    assert Fact.objects.values_list("date_kind", "date_2", "reliability").get(pk=birth.pk) == (
        "between",
        datetime.date(1825, 1, 1),
        "handed_down",
    )


@pytest.mark.django_db
def test_change_fact_keeps_the_chosen_citations_and_drops_the_others():
    kept = CitationFactory(page="fol. 12")
    CitationFactory(fact=kept.fact)

    change_fact(
        person_id=kept.fact.person.pk, fact_id=kept.fact.pk, **{**FIELDS, "citations": {kept.source.pk: "fol. 13"}}
    )

    assert list(Citation.objects.values_list("pk", "page")) == [(kept.pk, "fol. 13")]


@pytest.mark.django_db
def test_change_fact_moves_a_fact_from_the_person_to_the_partnership():
    partnership = PartnershipFactory()
    birth = FactFactory(person=partnership.person_a)

    change_fact(
        person_id=partnership.person_a.pk,
        fact_id=birth.pk,
        **{**FIELDS, "kind": Fact.Kind.MARRIAGE, "partner_id": partnership.person_b.pk},
    )

    assert Fact.objects.values_list("person", "partnership").get(pk=birth.pk) == (None, partnership.pk)


@pytest.mark.django_db
def test_change_fact_of_a_partnership_from_the_other_partner():
    partnership = PartnershipFactory()
    marriage = FactFactory(person=None, partnership=partnership, kind=Fact.Kind.MARRIAGE)

    change_fact(
        person_id=partnership.person_b.pk,
        fact_id=marriage.pk,
        **{**FIELDS, "kind": Fact.Kind.MARRIAGE, "partner_id": partnership.person_a.pk, "date": "1958"},
    )

    assert Fact.objects.values_list("partnership", "date_1").get(pk=marriage.pk) == (
        partnership.pk,
        datetime.date(1958, 1, 1),
    )


@pytest.mark.django_db
def test_change_fact_of_somebody_else():
    birth = FactFactory()
    stranger = PersonFactory(given_names="Fremd")

    with pytest.raises(Fact.DoesNotExist):
        change_fact(person_id=stranger.pk, fact_id=birth.pk, **FIELDS)


@pytest.mark.django_db
def test_delete_fact_removes_it_with_its_citations_but_not_the_source():
    citation = CitationFactory()

    result = delete_fact(person_id=citation.fact.person.pk, fact_id=citation.fact.pk)

    assert (result, Fact.objects.exists(), Citation.objects.exists(), Source.objects.exists()) == (
        None,
        False,
        False,
        True,
    )


@pytest.mark.django_db
def test_delete_fact_of_somebody_else():
    birth = FactFactory()
    stranger = PersonFactory(given_names="Fremd")

    with pytest.raises(Fact.DoesNotExist):
        delete_fact(person_id=stranger.pk, fact_id=birth.pk)
