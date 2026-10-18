from apps.family_tree.domain.relationship import FamilyGraph
from apps.family_tree.models import ParentChild, Partnership, Person, SiblingPair


def family_graph() -> FamilyGraph:
    """
    The whole tree as domain.relationship needs it, in four queries, to name how anyone is related to the home
    person - see docs/patterns/family.md.
    """
    return FamilyGraph.from_links(
        sex=dict(Person.objects.values_list("pk", "sex")),
        parent_child=ParentChild.objects.values_list("parent_id", "child_id"),
        partnerships=(
            (person_a, person_b, kind == Partnership.Kind.MARRIAGE)
            for person_a, person_b, kind in Partnership.objects.values_list("person_a_id", "person_b_id", "kind")
        ),
        sibling_pairs=SiblingPair.objects.values_list("person_a_id", "person_b_id"),
    )
