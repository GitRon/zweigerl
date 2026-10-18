from django.db.models import Min, Q

from apps.family_tree.domain.layout import (
    LayoutPerson,
    ParentLink,
    PartnerLink,
    SiblingLink,
    TreeLayout,
    layout,
)
from apps.family_tree.models import Fact, ParentChild, Partnership, Person, SiblingPair, TreeSettings


def tree_layout() -> TreeLayout:
    """
    The whole tree, laid out around the home person - or, while nobody has been chosen, around the person
    entered first. A person with several birth facts is sorted among their siblings by the earliest. See
    docs/patterns/tree-layout.md.
    """
    people = [
        LayoutPerson(id=person_id, birth=birth)
        for person_id, birth in Person.objects.annotate(
            birth=Min("facts__sort_date", filter=Q(facts__kind=Fact.Kind.BIRTH))
        )
        .order_by("pk")
        .values_list("pk", "birth")
    ]
    chosen = TreeSettings.objects.filter(pk=TreeSettings.ONLY_ROW).values_list("home_person_id", flat=True).first()

    return layout(
        people=people,
        partnerships=[
            PartnerLink(person_a=person_a, person_b=person_b)
            for person_a, person_b in Partnership.objects.order_by("pk").values_list("person_a", "person_b")
        ],
        parent_links=[
            ParentLink(parent=parent, child=child)
            for parent, child in ParentChild.objects.order_by("pk").values_list("parent", "child")
        ],
        sibling_links=[
            SiblingLink(person_a=person_a, person_b=person_b)
            for person_a, person_b in SiblingPair.objects.order_by("pk").values_list("person_a", "person_b")
        ],
        home_person_id=chosen or (people[0].id if people else None),
    )
