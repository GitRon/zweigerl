import factory

from apps.stammbaum.models import Partnerschaft
from apps.stammbaum.tests.factories.person import PersonFactory


class PartnerschaftFactory(factory.django.DjangoModelFactory):
    person_a = factory.SubFactory(PersonFactory)
    person_b = factory.SubFactory(PersonFactory)
    art = Partnerschaft.Art.EHE

    class Meta:
        model = Partnerschaft
