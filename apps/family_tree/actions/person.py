from django.db import models, transaction

from apps.family_tree.models import ParentChild, Partnership, Person, SiblingPair, TreeSettings


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
