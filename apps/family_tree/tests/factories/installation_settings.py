import factory

from apps.family_tree.models import InstallationSettings


class InstallationSettingsFactory(factory.django.DjangoModelFactory):
    """
    The one row of settings. "django_get_or_create" because there is only ever primary key 1.
    """

    id = InstallationSettings.ONLY_ROW

    class Meta:
        model = InstallationSettings
        django_get_or_create = ("id",)
