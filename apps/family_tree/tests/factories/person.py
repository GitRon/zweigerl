import factory

from apps.family_tree.models import Person
from apps.family_tree.tests.factories.tree import TreeFactory


class PersonFactory(factory.django.DjangoModelFactory):
    """
    An invented person - see docs/patterns/testing-data.md. Names from the Familie Huber's world, never real.
    """

    tree = factory.SubFactory(TreeFactory)
    given_names = factory.Iterator(["Anna", "Josef", "Theresia", "Franz", "Maria", "Johann"])
    surname = "Huber"
    sex = Person.Sex.UNKNOWN
    living_status = Person.LivingStatus.UNKNOWN

    class Meta:
        model = Person
