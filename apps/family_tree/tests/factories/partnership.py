import factory

from apps.family_tree.models import Partnership
from apps.family_tree.tests.factories.person import PersonFactory


class PartnershipFactory(factory.django.DjangoModelFactory):
    person_a = factory.SubFactory(PersonFactory)
    person_b = factory.SubFactory(PersonFactory)
    kind = Partnership.Kind.MARRIAGE

    class Meta:
        model = Partnership
