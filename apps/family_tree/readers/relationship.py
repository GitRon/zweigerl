from django.db.models import Q

from apps.family_tree.domain.relationship import FamilyGraph
from apps.family_tree.models import ParentChild, Partnership, Person, SiblingPair


def family_graph(*, tree_id: int, without_id: int | None = None) -> FamilyGraph:
    """
    The tree "tree_id" as domain.relationship needs it, in four queries, to name how anyone is related to the home
    person - see docs/patterns/family.md. "without_id" leaves that person and their links out: the tree as it
    would be once they are deleted (#19).
    """
    people = Person.objects.filter(tree=tree_id).exclude(pk=without_id)
    parent_child = ParentChild.objects.filter(child__tree=tree_id).exclude(Q(parent=without_id) | Q(child=without_id))
    partnerships = Partnership.objects.filter(person_a__tree=tree_id).exclude(
        Q(person_a=without_id) | Q(person_b=without_id)
    )
    sibling_pairs = SiblingPair.objects.filter(person_a__tree=tree_id).exclude(
        Q(person_a=without_id) | Q(person_b=without_id)
    )
    return FamilyGraph.from_links(
        sex=dict(people.values_list("pk", "sex")),
        parent_child=parent_child.values_list("parent_id", "child_id"),
        partnerships=(
            (person_a, person_b, kind == Partnership.Kind.MARRIAGE)
            for person_a, person_b, kind in partnerships.values_list("person_a_id", "person_b_id", "kind")
        ),
        sibling_pairs=sibling_pairs.values_list("person_a_id", "person_b_id"),
    )
