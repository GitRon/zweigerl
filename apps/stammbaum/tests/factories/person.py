import factory

from apps.stammbaum.models import Person


class PersonFactory(factory.django.DjangoModelFactory):
    """
    An invented person - see docs/patterns/testing-data.md. Names from the Familie Huber's world, never real.
    """

    vornamen = factory.Iterator(["Anna", "Josef", "Theresia", "Franz", "Maria", "Johann"])
    familienname = "Huber"
    geschlecht = Person.Geschlecht.UNBEKANNT
    lebensstatus = Person.Lebensstatus.UNBEKANNT

    class Meta:
        model = Person
