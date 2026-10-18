import factory

from apps.stammbaum.models import Zitat
from apps.stammbaum.tests.factories.angabe import AngabeFactory
from apps.stammbaum.tests.factories.quelle import QuelleFactory


class ZitatFactory(factory.django.DjangoModelFactory):
    angabe = factory.SubFactory(AngabeFactory)
    quelle = factory.SubFactory(QuelleFactory)
    stelle = "fol. 12"

    class Meta:
        model = Zitat
