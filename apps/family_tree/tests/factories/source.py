import factory

from apps.family_tree.models import Source
from apps.family_tree.tests.factories.tree import TreeFactory


class SourceFactory(factory.django.DjangoModelFactory):
    tree = factory.SubFactory(TreeFactory)
    title = factory.Sequence(lambda n: f"Taufbuch Mariazell, Band {n}")
    kind = Source.Kind.PARISH_REGISTER

    class Meta:
        model = Source
        skip_postgeneration_save = True

    @factory.post_generation
    def people(self, create, extracted, **kwargs):
        if create and extracted:
            self.people.set(extracted)
