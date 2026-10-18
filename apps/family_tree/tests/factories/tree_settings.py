import factory

from apps.family_tree.models import TreeSettings
from apps.family_tree.tests.factories.person import PersonFactory


class TreeSettingsFactory(factory.django.DjangoModelFactory):
    """
    The one row of settings. "django_get_or_create" because there is only ever primary key 1.
    """

    id = TreeSettings.ONLY_ROW
    home_person = factory.SubFactory(PersonFactory)

    class Meta:
        model = TreeSettings
        django_get_or_create = ("id",)
