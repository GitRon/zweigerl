import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError

from apps.family_tree.models import Citation, Fact
from apps.family_tree.tests.factories.citation import CitationFactory
from apps.family_tree.tests.factories.fact import FactFactory
from apps.family_tree.tests.factories.partnership import PartnershipFactory
from apps.family_tree.tests.factories.source import SourceFactory


def test_citation_str_names_fact_and_source():
    citation = CitationFactory.build(
        fact=FactFactory.build(as_value=True), source=SourceFactory.build(title="Volkszählung 1939")
    )

    assert str(citation) == "Beruf: Uhrmacher - Volkszählung 1939"


@pytest.mark.django_db
def test_citation_refuses_the_same_source_twice_on_save():
    citation = CitationFactory()

    with pytest.raises(ValidationError, match="Diese Angabe zitiert diese Quelle schon"):
        CitationFactory(fact=citation.fact, source=citation.source, page="fol. 13")


@pytest.mark.django_db
def test_citation_refuses_the_same_source_twice_in_the_database():
    citation = CitationFactory()

    with pytest.raises(IntegrityError, match=r"family_tree_citation\.fact_id, family_tree_citation\.source_id"):
        Citation.objects.bulk_create([Citation(fact=citation.fact, source=citation.source)])


@pytest.mark.django_db
def test_citation_keeps_a_cited_source_from_being_deleted():
    citation = CitationFactory()

    with pytest.raises(ProtectedError, match="protected foreign keys"):
        citation.source.delete()


def test_citation_clean_leaves_an_incomplete_citation_to_the_field_validation():
    assert Citation(page="Nr. 3").clean() is None


@pytest.mark.django_db
def test_citation_refuses_a_source_of_another_tree():
    fact = FactFactory()

    with pytest.raises(ValidationError, match="Die Quelle gehört zu einem anderen Stammbaum als die Angabe"):
        CitationFactory(fact=fact, source=SourceFactory(tree__name="Familie Berger"))


@pytest.mark.django_db
def test_citation_of_a_couple_cites_a_source_of_their_tree():
    marriage = FactFactory(person=None, partnership=PartnershipFactory(), kind=Fact.Kind.MARRIAGE)

    citation = CitationFactory(fact=marriage, source=SourceFactory())

    assert Citation.objects.get() == citation
