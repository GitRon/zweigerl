import factory

from apps.family_tree.models import GedcomImport
from apps.family_tree.tests.factories.tree import TreeFactory


class GedcomImportFactory(factory.django.DjangoModelFactory):
    """
    An import under an invented name.
    """

    tree = factory.SubFactory(TreeFactory)
    name = "PAF Huber"

    class Meta:
        model = GedcomImport
