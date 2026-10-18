import datetime

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from apps.family_tree.models import Fact, ParentChild, Partnership, Person, SiblingPair, TreeSettings


class Relation(models.TextChoices):
    # What the new person is to the one whose card they are added from (#18).
    PARENT = "parent", "Elternteil"
    PARTNER = "partner", "Partner"
    CHILD = "child", "Kind"
    SIBLING = "sibling", "Geschwister"


def create_person(*, given_names: str, surname: str, sex: str, living_status: str) -> Person:
    """
    Adds a person to the tree without connecting them to anybody (#18). The first person of an empty tree becomes
    the home person, so the tree has someone to be laid out around from the start. An invalid "sex" or
    "living_status" is refused with the constraint's "ValidationError".
    """
    with transaction.atomic():
        first = not Person.objects.exists()
        person = Person.objects.create(
            given_names=given_names.strip(), surname=surname.strip(), sex=sex, living_status=living_status
        )
        if first:
            TreeSettings.objects.update_or_create(pk=TreeSettings.ONLY_ROW, defaults={"home_person": person})
    return person


def add_relative(
    *, person_id: int, relation: str, given_names: str, surname: str, sex: str, living_status: str
) -> Person:
    """
    Adds a person as the parent, partner, child or sibling of "person_id" and connects the two (#18). A sibling
    shares the person's known parents - a full sibling - or, while nobody knows them, is stored as a SiblingPair.
    Raises "Person.DoesNotExist" for somebody no longer in the tree, "ValueError" for a relation that is none of
    "Relation", and the "ValidationError" of a rule the new link would break, a third birth parent for one;
    nothing is saved then.
    """
    relation = Relation(relation)
    with transaction.atomic():
        person = Person.objects.get(pk=person_id)
        relative = create_person(given_names=given_names, surname=surname, sex=sex, living_status=living_status)
        if relation == Relation.PARENT:
            ParentChild.objects.create(parent=relative, child=person)
        elif relation == Relation.PARTNER:
            Partnership.objects.create(person_a=person, person_b=relative)
        elif relation == Relation.CHILD:
            ParentChild.objects.create(parent=person, child=relative)
        else:
            _add_sibling(person=person, sibling=relative)
    return relative


def _add_sibling(*, person: Person, sibling: Person) -> None:
    parent_links = list(person.parent_links.all())
    if not parent_links:
        SiblingPair.objects.create(person_a=person, person_b=sibling)
    for link in parent_links:
        ParentChild.objects.create(
            parent_id=link.parent_id, child=sibling, partnership_id=link.partnership_id, pedigree=link.pedigree
        )


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
    with transaction.atomic():
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


def delete_person(*, person_id: int) -> Person:
    """
    Deletes a person with their facts, the facts of their partnerships, the citations of both and every link to
    them (#19). Their sources stay, and so do the people they were connected to, whether still connected to the
    home person or not. Returns the person as they were.

    Raises "Person.DoesNotExist" for somebody not in the tree and "ValidationError" for the home person, who is
    deleted only once another one is chosen.
    """
    with transaction.atomic():
        person = Person.objects.get(pk=person_id)
        if TreeSettings.objects.filter(home_person=person).exists():
            raise ValidationError(
                "Das ist die Ausgangsperson. Wähl erst eine andere Ausgangsperson, dann lässt sie sich löschen."
            )
        # Everything that goes with them goes by CASCADE: their facts, their links, their partnerships and with
        # those the couple's facts, and the citations of all of them. A source is a row of its own and stays.
        person.delete()
    return person


def unlink_relative(*, person_id: int, relation: str, relative_id: int) -> None:
    """
    Removes the one link that makes "relative_id" the parent, partner, child or explicit sibling of "person_id"
    (#19) - for both of them, since the link is one row. A partnership takes the couple's facts with it, and its
    children stay the children of each of the two. Nobody is deleted, whoever hangs loose afterwards.

    Raises "ValueError" for a relation that is none of "Relation" and "ObjectDoesNotExist" when no such link
    joins the two - a sibling through a shared parent is joined by the parent's links, not one of their own.
    """
    relation = Relation(relation)
    with transaction.atomic():
        if relation == Relation.PARENT:
            links = ParentChild.objects.filter(parent=relative_id, child=person_id)
        elif relation == Relation.CHILD:
            links = ParentChild.objects.filter(parent=person_id, child=relative_id)
        elif relation == Relation.PARTNER:
            links = Partnership.objects.filter(
                Q(person_a=person_id, person_b=relative_id) | Q(person_a=relative_id, person_b=person_id)
            )
        else:
            links = SiblingPair.objects.filter(
                Q(person_a=person_id, person_b=relative_id) | Q(person_a=relative_id, person_b=person_id)
            )
        deleted, _ = links.delete()
        if not deleted:
            raise ObjectDoesNotExist("Keine solche Verbindung zwischen den beiden.")
