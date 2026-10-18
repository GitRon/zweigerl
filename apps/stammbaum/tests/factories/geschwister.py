import factory

from apps.stammbaum.models import Geschwister
from apps.stammbaum.tests.factories.person import PersonFactory


class GeschwisterFactory(factory.django.DjangoModelFactory):
    person_a = factory.SubFactory(PersonFactory)
    person_b = factory.SubFactory(PersonFactory)

    class Meta:
        model = Geschwister
