import factory

from apps.family_tree.models import GedcomImport


class GedcomImportFactory(factory.django.DjangoModelFactory):
    """
    An import under an invented name.
    """

    name = "PAF Huber"

    class Meta:
        model = GedcomImport
