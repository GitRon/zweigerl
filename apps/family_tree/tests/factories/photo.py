import datetime

import factory

from apps.family_tree.models import Photo
from apps.family_tree.tests.factories.tree import TreeFactory


class PhotoFactory(factory.django.DjangoModelFactory):
    tree = factory.SubFactory(TreeFactory)
    file = factory.Sequence(lambda n: f"photos/{n}/original.jpg")

    class Meta:
        model = Photo

    class Params:
        # Taken "um 1950", as most old photos are.
        about_1950 = factory.Trait(date_kind="about", date_1=datetime.date(1950, 1, 1), precision="year")
