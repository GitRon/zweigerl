import factory

from apps.family_tree.models import SiblingPair
from apps.family_tree.tests.factories.person import PersonFactory


class SiblingPairFactory(factory.django.DjangoModelFactory):
    person_a = factory.SubFactory(PersonFactory)
    person_b = factory.SubFactory(PersonFactory)

    class Meta:
        model = SiblingPair
