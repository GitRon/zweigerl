import datetime

import pytest

from apps.family_tree.models import Fact
from apps.family_tree.readers.evidence import facts, sources
from apps.family_tree.tests.factories.citation import CitationFactory
from apps.family_tree.tests.factories.fact import FactFactory
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.source import SourceFactory


@pytest.mark.django_db
def test_facts__lists_a_persons_facts_in_date_order_undated_last():
    lena = PersonFactory()
    occupation = FactFactory(person=lena, as_value=True)
    death = FactFactory(person=lena, kind=Fact.Kind.DEATH, date_1=datetime.date(2009, 11, 14))
    birth = FactFactory(person=lena)
    FactFactory()
    FactFactory(person=None, partnership=PartnershipFactory(person_a=lena), kind=Fact.Kind.MARRIAGE)

    assert list(facts(person=lena)) == [birth, death, occupation]


@pytest.mark.django_db
def test_facts__marks_documented_without_citation_as_undocumented():
    lena = PersonFactory()
    ohne_citation = FactFactory(person=lena)
    mit_citation = CitationFactory(fact__person=lena, fact__as_value=True).fact
    probable_fact = FactFactory(person=lena, kind=Fact.Kind.BAPTISM, reliability=Fact.Reliability.PROBABLE)

    result = set(facts(person=lena).values_list("pk", "undocumented"))

    assert result == {(ohne_citation.pk, True), (mit_citation.pk, False), (probable_fact.pk, False)}


@pytest.mark.django_db
def test_sources_are_filed_with_the_person_or_cited_by_their_facts():
    lena = PersonFactory()
    filed = SourceFactory(title="Geburtsurkunde", people=[lena])
    cited = CitationFactory(fact__person=lena, source__title="Studienunterlagen").source
    CitationFactory(fact__person=lena, fact__as_value=True, source=filed)
    SourceFactory(title="Fremde Quelle")

    assert list(sources(person=lena)) == [filed, cited]


@pytest.mark.django_db
def test_sources_include_those_of_the_persons_partnerships():
    lena, markus = PersonFactory.create_batch(2)
    couple = PartnershipFactory(person_a=markus, person_b=lena)
    marriage_certificate = CitationFactory(
        fact__person=None, fact__partnership=couple, fact__kind=Fact.Kind.MARRIAGE
    ).source

    assert list(sources(person=lena)) == [marriage_certificate]
