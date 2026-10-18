import factory

from apps.stammbaum.models import Einstellung
from apps.stammbaum.tests.factories.person import PersonFactory


class EinstellungFactory(factory.django.DjangoModelFactory):
    """
    The one row of settings. "django_get_or_create" because there is only ever primary key 1.
    """

    id = Einstellung.EINZIGE_ZEILE
    ausgangsperson = factory.SubFactory(PersonFactory)

    class Meta:
        model = Einstellung
        django_get_or_create = ("id",)
