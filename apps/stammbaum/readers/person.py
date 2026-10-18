from dataclasses import dataclass

from django.db.models import Q

from apps.stammbaum.models import Geschwister, Person


@dataclass(frozen=True, kw_only=True)
class Verwandte:
    eltern: list[Person]
    partner: list[Person]
    kinder: list[Person]
    geschwister: list[Person]


def verwandte(*, person: Person) -> Verwandte:
    """
    Everyone directly related to "person", each list in the people's own order. Siblings are those who share
    a parent with them, plus the ones stored explicitly because no shared parent is known - see
    docs/patterns/familie.md.
    """
    eltern = Person.objects.filter(kind_verbindungen__kind=person)
    geschwister = Person.objects.filter(
        Q(eltern_verbindungen__elternteil__in=eltern)
        | Q(pk__in=Geschwister.objects.filter(person_b=person).values("person_a"))
        | Q(pk__in=Geschwister.objects.filter(person_a=person).values("person_b"))
    )

    return Verwandte(
        eltern=list(eltern),
        partner=list(
            Person.objects.filter(
                Q(partnerschaften_als_a__person_b=person) | Q(partnerschaften_als_b__person_a=person)
            ).distinct()
        ),
        kinder=list(Person.objects.filter(eltern_verbindungen__elternteil=person).distinct()),
        geschwister=list(geschwister.exclude(pk=person.pk).distinct()),
    )
