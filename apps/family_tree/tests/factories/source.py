import factory

from apps.family_tree.models import Source


class SourceFactory(factory.django.DjangoModelFactory):
    title = factory.Sequence(lambda n: f"Taufbuch Mariazell, Band {n}")
    kind = Source.Kind.PARISH_REGISTER

    class Meta:
        model = Source
        skip_postgeneration_save = True

    @factory.post_generation
    def people(self, create, extracted, **kwargs):
        if create and extracted:
            self.people.set(extracted)
