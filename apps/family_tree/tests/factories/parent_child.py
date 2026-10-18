import factory

from apps.family_tree.models import ParentChild
from apps.family_tree.tests.factories.person import PersonFactory


class ParentChildFactory(factory.django.DjangoModelFactory):
    parent = factory.SubFactory(PersonFactory)
    child = factory.SubFactory(PersonFactory)
    pedigree = ParentChild.Pedigree.BIRTH

    class Meta:
        model = ParentChild
