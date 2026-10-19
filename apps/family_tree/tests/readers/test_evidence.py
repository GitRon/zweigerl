import datetime

import pytest

from apps.family_tree.models import Fact
from apps.family_tree.readers.evidence import facts, source_deletion, source_file_deletion, sources
from apps.family_tree.tests.factories.citation import CitationFactory
from apps.family_tree.tests.factories.fact import FactFactory
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.source import SourceFactory
from apps.family_tree.tests.factories.source_file import SourceFileFactory


@pytest.mark.django_db
def test_facts__lists_a_persons_facts_in_date_order_undated_last():
    lena = PersonFactory()
    occupation = FactFactory(person=lena, as_value=True)
    death = FactFactory(person=lena, kind=Fact.Kind.DEATH, date_1=datetime.date(2009, 11, 14))
    birth = FactFactory(person=lena)
    FactFactory()

    assert list(facts(person=lena)) == [birth, death, occupation]


@pytest.mark.django_db
def test_facts__include_those_of_the_persons_partnerships_on_either_side():
    lena = PersonFactory()
    first = FactFactory(
        person=None,
        partnership=PartnershipFactory(person_a=lena),
        kind=Fact.Kind.MARRIAGE,
        date_1=datetime.date(1958, 5, 3),
    )
    second = FactFactory(
        person=None,
        partnership=PartnershipFactory(person_b=lena),
        kind=Fact.Kind.MARRIAGE,
        date_1=datetime.date(1970, 6, 1),
    )
    FactFactory(person=None, partnership=PartnershipFactory(), kind=Fact.Kind.MARRIAGE)

    assert list(facts(person=lena)) == [first, second]


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


@pytest.mark.django_db
def test_source_deletion_of_a_source_not_there_is_none():
    assert source_deletion(source_id=404) is None


@pytest.mark.django_db
def test_source_deletion_counts_the_files_and_names_the_facts_citing_it():
    lena = PersonFactory(given_names="Lena", surname="Huber")
    johann = PersonFactory(given_names="Johann", surname="Huber")
    maria = PersonFactory(given_names="Maria", surname="Huber")
    register = SourceFileFactory().source
    SourceFileFactory(source=register)
    CitationFactory(source=register, fact=FactFactory(person=lena))
    marriage = FactFactory(
        person=None, partnership=PartnershipFactory(person_a=johann, person_b=maria), kind=Fact.Kind.MARRIAGE
    )
    CitationFactory(source=register, fact=marriage)
    CitationFactory(fact=FactFactory(person=lena, kind=Fact.Kind.DEATH))

    deletion = source_deletion(source_id=register.pk)

    assert (deletion.source, deletion.file_count, sorted(deletion.citing)) == (
        register,
        2,
        ["Geboren · Lena Huber", "Geheiratet · Johann Huber und Maria Huber"],
    )


@pytest.mark.django_db
def test_source_file_deletion_numbers_the_file_as_the_card_does():
    first = SourceFileFactory()
    second = SourceFileFactory(source=first.source)
    SourceFileFactory()

    deletion = source_file_deletion(source_id=first.source.pk, file_id=second.pk)

    assert (deletion.source_file, deletion.number) == (second, 2)


@pytest.mark.django_db
def test_source_file_deletion_of_a_file_of_another_source_is_none():
    scan = SourceFileFactory()

    assert source_file_deletion(source_id=SourceFactory().pk, file_id=scan.pk) is None
