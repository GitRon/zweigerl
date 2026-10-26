"""
Two people who are one person become one (#85) - mostly those a second import brought in again. What happens to
which row is docs/patterns/family.md, "Merging two people".
"""

from collections.abc import Iterable

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from apps.family_tree.models import ParentChild, Partnership, Person, SiblingPair, TreeSettings
from apps.family_tree.models.person import NAME_AND_STATUS_FIELDS

# Two families of the same couple become one, which is what the better known of the two says it was.
_KIND_ORDER = (Partnership.Kind.MARRIAGE, Partnership.Kind.COHABITATION, Partnership.Kind.UNKNOWN)


def merge_persons(*, person_id: int, other_id: int, from_other: Iterable[str]) -> Person:
    """
    Merges "other_id" into "person_id", who stays, and deletes "other_id" (#85). Every fact, note, photo and filed
    source of the other goes to the person, each keeping its citations and its Herkunft, and so does every link:
    a family with a partner both had becomes one, its children united, and a link both had is kept once with
    what both kept raw. The fields named in "from_other" - out of "NAME_AND_STATUS_FIELDS" - are the other's,
    every other one the person's; what the other kept raw is kept beside the person's. The Herkunft of the person
    is the person's. Nothing of it can be undone.

    Raises "Person.DoesNotExist" for somebody not in the tree, and "ValidationError" for two people who cannot be
    one: the same person, a couple, an ancestor and their descendant, or two whose birth parents would be more
    than two - those are merged first.
    """
    from_other = set(from_other)
    with transaction.atomic():
        person = Person.objects.get(pk=person_id)
        other = Person.objects.get(pk=other_id)
        _refuse(person=person, other=other)

        merged = _merge_partnerships(person=person, other=other)
        _drop_sibling_pairs(person=person, other=other)
        _move_sibling_pairs(person=person, other=other)
        _move_child_links(person=person, other=other, merged=merged)
        Partnership.objects.filter(pk__in=merged).delete()
        _move_parent_links(person=person, other=other)
        for row in [*other.facts.all(), *other.notes.all()]:
            row.person = person
            row.save()
        _move_photo_links(person=person, other=other)
        person.filed_sources.add(*other.filed_sources.all())
        settings = TreeSettings.objects.filter(home_person=other).first()
        if settings is not None:
            settings.home_person = person
            settings.save()

        for field in NAME_AND_STATUS_FIELDS:
            if field in from_other:
                setattr(person, field, getattr(other, field))
        person.gedcom_raw = [*person.gedcom_raw, *other.gedcom_raw]
        other.delete()
        person.full_clean()
        person.save()
    return person


def _refuse(*, person: Person, other: Person) -> None:
    """
    Refuses two people who cannot be one. A couple, or an ancestor and a descendant, are two by what the tree
    says, and as one they would be their own partner or ancestor. More than two birth parents would break the
    rule of docs/patterns/family.md: they are a pair of parents who are the same people, and merging them first
    leaves two.
    """
    if person.pk == other.pk:
        raise ValidationError("Eine Person lässt sich nicht mit sich selbst zusammenführen.")
    if Partnership.objects.filter(_pair(first=person.pk, second=other.pk)).exists():
        raise ValidationError("Die beiden sind ein Paar, also zwei Personen.")
    if other.pk in _ancestors(person_id=person.pk) or person.pk in _ancestors(person_id=other.pk):
        raise ValidationError("Ein Vorfahr und sein Nachkomme sind zwei Personen.")
    parents = set(ParentChild.objects.filter(child=person).values_list("parent", flat=True))
    birth_parents = {
        *ParentChild.objects.filter(child=person, pedigree=ParentChild.Pedigree.BIRTH).values_list("parent", flat=True),
        *ParentChild.objects.filter(child=other, pedigree=ParentChild.Pedigree.BIRTH)
        .exclude(parent__in=parents)
        .values_list("parent", flat=True),
    }
    if len(birth_parents) > ParentChild.MAX_BIRTH_PARENTS:
        raise ValidationError(
            f"Zusammen hätten die beiden {len(birth_parents)} leibliche Eltern. "
            "Führ zuerst die Eltern zusammen, die dieselben sind."
        )


def _ancestors(*, person_id: int) -> set[int]:
    generation, seen = {person_id}, set()
    while generation:
        generation = set(ParentChild.objects.filter(child__in=generation).values_list("parent", flat=True)) - seen
        seen |= generation
    return seen


def _merge_partnerships(*, person: Person, other: Person) -> dict[int, Partnership]:
    """
    Gives the other's partnerships to the person. A partner both had makes one family of two: the person's keeps
    its row and takes the facts and the raw of the other's, and the partner's links to the other's children with
    it. Returns the partnership each such one of the other's became, by its id - the other's links to the children
    follow it in "_move_child_links", and then it goes.
    """
    merged = {}
    for partnership in Partnership.objects.filter(Q(person_a=other) | Q(person_b=other)):
        partner_id = partnership.person_b_id if partnership.person_a_id == other.pk else partnership.person_a_id
        existing = Partnership.objects.filter(_pair(first=person.pk, second=partner_id)).first()
        if existing is None:
            if partnership.person_a_id == other.pk:
                partnership.person_a = person
            else:
                partnership.person_b = person
            partnership.save()
            continue

        existing.kind = min(existing.kind, partnership.kind, key=_KIND_ORDER.index)
        existing.gedcom_raw = [*existing.gedcom_raw, *partnership.gedcom_raw]
        existing.save()
        for row in [*partnership.facts.all(), *partnership.child_links.filter(parent=partner_id)]:
            row.partnership = existing
            row.save()
        merged[partnership.pk] = existing
    return merged


def _drop_sibling_pairs(*, person: Person, other: Person) -> None:
    """
    Deletes the explicit sibling pairs the merge makes siblings through a parent - see docs/patterns/family.md,
    no pair stands beside a shared parent - with what they kept raw: the two themselves, somebody who shares a
    parent of either, and a child of one with a child of the other. Before any link moves, since a link is
    refused while such a pair is still there.
    """
    parents = set(ParentChild.objects.filter(child__in=(person, other)).values_list("parent", flat=True))
    for pair in SiblingPair.objects.filter(_either(person_id=person.pk) | _either(person_id=other.pk)):
        sibling_id = pair.person_b_id if pair.person_a_id in (person.pk, other.pk) else pair.person_a_id
        if (
            sibling_id in (person.pk, other.pk)
            or ParentChild.objects.filter(child=sibling_id, parent__in=parents).exists()
        ):
            pair.delete()
    children_of_person = ParentChild.objects.filter(parent=person).values("child")
    children_of_other = ParentChild.objects.filter(parent=other).values("child")
    SiblingPair.objects.filter(
        Q(person_a__in=children_of_person, person_b__in=children_of_other)
        | Q(person_a__in=children_of_other, person_b__in=children_of_person)
    ).delete()


def _move_sibling_pairs(*, person: Person, other: Person) -> None:
    # The other's explicit siblings become the person's, a sibling of both once, with the raw of both pairs.
    for pair in SiblingPair.objects.filter(_either(person_id=other.pk)):
        sibling_id = pair.person_b_id if pair.person_a_id == other.pk else pair.person_a_id
        existing = SiblingPair.objects.filter(_pair(first=person.pk, second=sibling_id)).first()
        if existing is None:
            if pair.person_a_id == other.pk:
                pair.person_a = person
            else:
                pair.person_b = person
            pair.save()
        else:
            pair.delete()
            existing.gedcom_raw = [*existing.gedcom_raw, *pair.gedcom_raw]
            existing.save()


def _move_child_links(*, person: Person, other: Person, merged: dict[int, Partnership]) -> None:
    # A child of both keeps the person's link, with its pedigree and its couple, and the raw of both. The other's
    # goes first, so the person's is not saved beside a third parent that is about to go.
    for link in other.child_links.all():
        existing = ParentChild.objects.filter(parent=person, child=link.child_id).first()
        if existing is None:
            link.parent = person
            link.partnership = merged.get(link.partnership_id, link.partnership)
            link.save()
        else:
            link.delete()
            existing.gedcom_raw = [*existing.gedcom_raw, *link.gedcom_raw]
            existing.save()


def _move_parent_links(*, person: Person, other: Person) -> None:
    for link in other.parent_links.all():
        existing = ParentChild.objects.filter(parent=link.parent_id, child=person).first()
        if existing is None:
            link.child = person
            link.save()
        else:
            link.delete()
            existing.gedcom_raw = [*existing.gedcom_raw, *link.gedcom_raw]
            existing.save()


def _move_photo_links(*, person: Person, other: Person) -> None:
    # The person's portrait stays theirs; the other's becomes it only for a person without one.
    for link in other.photo_links.all():
        portrait = link.is_portrait and not person.photo_links.filter(is_portrait=True).exists()
        existing = person.photo_links.filter(photo=link.photo_id).first()
        if existing is None:
            link.person = person
            link.is_portrait = portrait
            link.save()
        else:
            link.delete()
            existing.is_portrait = existing.is_portrait or portrait
            existing.save()


def _pair(*, first: int, second: int) -> Q:
    # A Partnership or a SiblingPair of the two, whichever of them is "person_a".
    return Q(person_a=first, person_b=second) | Q(person_a=second, person_b=first)


def _either(*, person_id: int) -> Q:
    return Q(person_a=person_id) | Q(person_b=person_id)
