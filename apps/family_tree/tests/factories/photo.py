import datetime

import factory

from apps.family_tree.models import Photo


class PhotoFactory(factory.django.DjangoModelFactory):
    file = factory.Sequence(lambda n: f"photos/{n}/original.jpg")

    class Meta:
        model = Photo

    class Params:
        # Taken "um 1950", as most old photos are.
        about_1950 = factory.Trait(date_kind="about", date_1=datetime.date(1950, 1, 1), precision="year")
