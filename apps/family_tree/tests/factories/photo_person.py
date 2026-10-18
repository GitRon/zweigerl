import factory

from apps.family_tree.models import PhotoPerson
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.photo import PhotoFactory


class PhotoPersonFactory(factory.django.DjangoModelFactory):
    photo = factory.SubFactory(PhotoFactory)
    person = factory.SubFactory(PersonFactory)

    class Meta:
        model = PhotoPerson
