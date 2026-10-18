import factory

from apps.family_tree.models import Citation
from apps.family_tree.tests.factories.fact import FactFactory
from apps.family_tree.tests.factories.source import SourceFactory


class CitationFactory(factory.django.DjangoModelFactory):
    fact = factory.SubFactory(FactFactory)
    source = factory.SubFactory(SourceFactory)
    page = "fol. 12"

    class Meta:
        model = Citation
