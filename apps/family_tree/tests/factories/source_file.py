import factory

from apps.family_tree.models import SourceFile
from apps.family_tree.tests.factories.source import SourceFactory


class SourceFileFactory(factory.django.DjangoModelFactory):
    source = factory.SubFactory(SourceFactory)
    file = factory.Sequence(lambda n: f"sources/1/{n}.pdf")

    class Meta:
        model = SourceFile
