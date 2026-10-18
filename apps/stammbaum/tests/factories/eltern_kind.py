import factory

from apps.stammbaum.models import ElternKind
from apps.stammbaum.tests.factories.person import PersonFactory


class ElternKindFactory(factory.django.DjangoModelFactory):
    elternteil = factory.SubFactory(PersonFactory)
    kind = factory.SubFactory(PersonFactory)
    art = ElternKind.Art.LEIBLICH

    class Meta:
        model = ElternKind
