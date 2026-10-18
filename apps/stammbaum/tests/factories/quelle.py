import factory

from apps.stammbaum.models import Quelle


class QuelleFactory(factory.django.DjangoModelFactory):
    titel = factory.Sequence(lambda n: f"Taufbuch Mariazell, Band {n}")
    art = Quelle.Art.MATRIKEN

    class Meta:
        model = Quelle
        skip_postgeneration_save = True

    @factory.post_generation
    def personen(self, create, extracted, **kwargs):
        if create and extracted:
            self.personen.set(extracted)
