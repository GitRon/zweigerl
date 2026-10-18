from apps.family_tree.models import Person, TreeSettings


def choose_home_person(*, person_id: int) -> TreeSettings:
    """
    Makes the person the home person, whom the tree is laid out around and relationships are named from
    (#20). Raises "Person.DoesNotExist" for somebody who is not in the tree, deleted in the meantime perhaps.
    """
    tree_settings, _ = TreeSettings.objects.update_or_create(
        pk=TreeSettings.ONLY_ROW, defaults={"home_person": Person.objects.get(pk=person_id)}
    )
    return tree_settings
