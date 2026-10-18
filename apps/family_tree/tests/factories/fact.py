import datetime

import factory

from apps.family_tree.models import Fact
from apps.family_tree.tests.factories.person import PersonFactory


class FactFactory(factory.django.DjangoModelFactory):
    """
    A birth date by default. "as_value" makes it a fact with a value instead (an occupation), and "between"
    a date range.
    """

    person = factory.SubFactory(PersonFactory)
    kind = Fact.Kind.BIRTH
    date_kind = Fact.DateKindChoice.EXACT
    date_1 = datetime.date(1931, 3, 12)
    precision = Fact.PrecisionChoice.DAY

    class Meta:
        model = Fact

    class Params:
        as_value = factory.Trait(kind=Fact.Kind.OCCUPATION, value="Uhrmacher", date_kind="", date_1=None, precision="")
        between = factory.Trait(
            date_kind=Fact.DateKindChoice.BETWEEN,
            date_1=datetime.date(1820, 1, 1),
            date_2=datetime.date(1830, 1, 1),
            precision=Fact.PrecisionChoice.YEAR,
        )
