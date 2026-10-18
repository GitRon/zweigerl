import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.family_tree.models import Fact, Person


@transaction.atomic
def change_name_and_status(
    *,
    person_id: int,
    given_names: str,
    surname: str,
    call_name: str,
    sex: str,
    living_status: str,
    death_year: int | None,
) -> Person:
    """
    Corrects a person's names, sex and whether they are alive (#30). A person now deceased with a "death_year"
    and no death fact yet gets one, for that year - marked documented, so it shows as "unbelegt" until it cites
    a source. A death fact already recorded is left as it is, whatever the status: editing facts is #14.

    Raises "Person.DoesNotExist" for somebody not in the tree, and "ValidationError" with a German message for
    a value the person cannot have or a death year in the future.
    """
    person = Person.objects.get(pk=person_id)
    person.given_names = given_names.strip()
    person.surname = surname.strip()
    person.call_name = call_name.strip()
    person.sex = sex
    person.living_status = living_status
    # "full_clean" rather than only the constraints "save" checks: it also holds the length of each name.
    person.full_clean()
    person.save()

    if (
        death_year is not None
        and living_status == Person.LivingStatus.DECEASED
        and not person.facts.filter(kind=Fact.Kind.DEATH).exists()
    ):
        if not 1 <= death_year <= timezone.localdate().year:
            raise ValidationError("Das Sterbejahr ist eine Jahreszahl, höchstens die heurige.")
        Fact.objects.create(
            person=person,
            kind=Fact.Kind.DEATH,
            date_kind=Fact.DateKindChoice.EXACT,
            date_1=datetime.date(death_year, 1, 1),
            precision=Fact.PrecisionChoice.YEAR,
        )

    return person
