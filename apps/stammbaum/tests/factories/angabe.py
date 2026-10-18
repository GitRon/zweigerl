import datetime

import factory

from apps.stammbaum.models import Angabe
from apps.stammbaum.tests.factories.person import PersonFactory


class AngabeFactory(factory.django.DjangoModelFactory):
    """
    A birth date by default. "als_wert" makes it an Angabe with a value instead (an occupation), and
    "zwischen" a date range.
    """

    person = factory.SubFactory(PersonFactory)
    art = Angabe.Art.GEBOREN
    datum_art = Angabe.DatumsArt.GENAU
    datum_1 = datetime.date(1931, 3, 12)
    genauigkeit = Angabe.DatumsGenauigkeit.TAG

    class Meta:
        model = Angabe

    class Params:
        als_wert = factory.Trait(art=Angabe.Art.BERUF, wert="Uhrmacher", datum_art="", datum_1=None, genauigkeit="")
        zwischen = factory.Trait(
            datum_art=Angabe.DatumsArt.ZWISCHEN,
            datum_1=datetime.date(1820, 1, 1),
            datum_2=datetime.date(1830, 1, 1),
            genauigkeit=Angabe.DatumsGenauigkeit.JAHR,
        )
