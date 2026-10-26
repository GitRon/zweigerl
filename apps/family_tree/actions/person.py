import datetime

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from apps.family_tree.models import Fact, ParentChild, Partnership, Person, SiblingPair, Tree


class Relation(models.TextChoices):
    # What the new person is to the one whose card they are added from (#18).
    PARENT = "parent", "Elternteil"
    PARTNER = "partner", "Partner"
    CHILD = "child", "Kind"
    SIBLING = "sibling", "Geschwister"


def create_person(*, tree_id: int, given_names: str, surname: str, sex: str, living_status: str) -> Person:
    """
    Adds a person to the tree "tree_id" without connecting them to anybody (#18). The first person of an empty tree
    becomes its home person, so the tree has someone to be laid out around from the start. Raises
    "Tree.DoesNotExist" for a tree that is not there, and the constraint's "ValidationError" for an invalid "sex"
    or "living_status".
    """
    with transaction.atomic():
        tree = Tree.objects.get(pk=tree_id)
        first = not tree.people.exists()
        person = Person.objects.create(
            tree=tree, given_names=given_names.strip(), surname=surname.strip(), sex=sex, living_status=living_status
        )
        if first:
            tree.home_person = person
            tree.save()
    return person


def add_relative(
    *,
    person_id: int,
    relation: str,
    given_names: str,
    surname: str,
    sex: str,
    living_status: str,
    partnership_id: int | None = None,
    pair_with_parent: bool = False,
) -> Person:
    """
    Adds a person to the tree of "person_id" as their parent, partner, child or sibling and connects the two
    (#18), the way "link_relative" connects somebody already in the tree - see there for "partnership_id" and
    "pair_with_parent". Raises what "link_relative" raises; nothing is saved then.
    """
    relation = Relation(relation)
    with transaction.atomic():
        person = Person.objects.get(pk=person_id)
        relative = create_person(
            tree_id=person.tree_id, given_names=given_names, surname=surname, sex=sex, living_status=living_status
        )
        _connect(
            person=person,
            relative=relative,
            relation=relation,
            partnership_id=partnership_id,
            pair_with_parent=pair_with_parent,
        )
    return relative


def link_relative(
    *,
    person_id: int,
    relation: str,
    relative_id: int,
    partnership_id: int | None = None,
    pair_with_parent: bool = False,
) -> Person:
    """
    Connects "relative_id", somebody already in the tree, as the parent, partner, child or sibling of "person_id"
    (#89), and returns them.

    - A child joins "partnership_id", a couple "person_id" is part of, as the child of both; without it, of the
      person alone.
    - A parent of a child with one parent so far joins the couple the two parents are; while they are none,
      "pair_with_parent" makes them one.
    - A sibling gets the person's parents - or, while nobody knows those, gives their own to the person - so the
      two are full siblings; while neither has known parents they are stored as a SiblingPair.

    Raises "Person.DoesNotExist" or "Partnership.DoesNotExist" for somebody or a couple no longer in the tree,
    "ValueError" for a relation that is none of "Relation", and "ValidationError" for a link the family's rules
    refuse: somebody as their own relative or ancestor, a third birth parent, a link already there, somebody of
    another tree (#34). Nothing is saved then.
    """
    relation = Relation(relation)
    with transaction.atomic():
        person = Person.objects.get(pk=person_id)
        relative = Person.objects.get(pk=relative_id)
        if relative.pk == person.pk:
            raise ValidationError("Niemand ist sein eigener Verwandter.")
        if relative.tree_id != person.tree_id:
            raise ValidationError("Die beiden gehören zu verschiedenen Stammbäumen.")
        _connect(
            person=person,
            relative=relative,
            relation=relation,
            partnership_id=partnership_id,
            pair_with_parent=pair_with_parent,
        )
    return relative


def _connect(
    *, person: Person, relative: Person, relation: Relation, partnership_id: int | None, pair_with_parent: bool
) -> None:
    if relation == Relation.PARENT:
        _add_parent(child=person, parent=relative, pair_with_parent=pair_with_parent)
    elif relation == Relation.PARTNER:
        Partnership.objects.create(person_a=person, person_b=relative)
    elif relation == Relation.CHILD:
        _add_child(parent=person, child=relative, partnership_id=partnership_id)
    else:
        _add_sibling(person=person, sibling=relative)


def _add_parent(*, child: Person, parent: Person, pair_with_parent: bool) -> None:
    _refuse_own_ancestor(parent_id=parent.pk, child_id=child.pk)
    partnership = None
    other_links = list(child.parent_links.exclude(parent=parent))
    if len(other_links) == 1:
        other = other_links[0]
        partnership = Partnership.objects.filter(
            Q(person_a=other.parent_id, person_b=parent.pk) | Q(person_a=parent.pk, person_b=other.parent_id)
        ).first()
        if partnership is None and pair_with_parent:
            partnership = Partnership.objects.create(person_a=other.parent, person_b=parent)
        if partnership is not None and other.partnership_id is None:
            other.partnership = partnership
            other.save()
    ParentChild.objects.create(parent=parent, child=child, partnership=partnership)


def _add_child(*, parent: Person, child: Person, partnership_id: int | None) -> None:
    _refuse_own_ancestor(parent_id=parent.pk, child_id=child.pk)
    partnership = Partnership.objects.get(pk=partnership_id) if partnership_id is not None else None
    # "ParentChild.clean" refuses a partnership the parent is not part of, before the other parent is looked at.
    ParentChild.objects.create(parent=parent, child=child, partnership=partnership)
    if partnership is None:
        return
    other_id = partnership.person_b_id if partnership.person_a_id == parent.pk else partnership.person_a_id
    link = ParentChild.objects.filter(parent=other_id, child=child).first()
    if link is None:
        ParentChild.objects.create(parent_id=other_id, child=child, partnership=partnership)
    elif link.partnership_id is None:
        link.partnership = partnership
        link.save()


def _add_sibling(*, person: Person, sibling: Person) -> None:
    if ParentChild.objects.filter(child=sibling, parent__child_links__child=person).exists():
        raise ValidationError("Die beiden haben einen gemeinsamen Elternteil und sind darüber schon Geschwister.")
    parent_links, child = list(person.parent_links.all()), sibling
    if not parent_links:
        parent_links, child = list(sibling.parent_links.all()), person
    if not parent_links:
        SiblingPair.objects.create(person_a=person, person_b=sibling)
    for link in parent_links:
        _refuse_own_ancestor(parent_id=link.parent_id, child_id=child.pk)
        ParentChild.objects.create(
            parent_id=link.parent_id, child=child, partnership_id=link.partnership_id, pedigree=link.pedigree
        )


def _refuse_own_ancestor(*, parent_id: int, child_id: int) -> None:
    """
    Refuses a parent link that would make somebody their own ancestor - the child already among the parent's
    ancestors. No constraint can hold a rule across generations, see docs/patterns/app-layout.md.
    """
    generation, seen = {parent_id}, set()
    while generation:
        if child_id in generation:
            raise ValidationError("Niemand ist sein eigener Vorfahr.")
        seen |= generation
        generation = set(ParentChild.objects.filter(child__in=generation).values_list("parent", flat=True)) - seen


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
        if Tree.objects.filter(home_person=person).exists():
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
