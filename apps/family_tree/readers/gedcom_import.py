from apps.family_tree.models import Person


def tree_is_empty() -> bool:
    """
    Whether nobody is in the tree yet, which decides what the import on the settings page says (#25, #85).
    """
    return not Person.objects.exists()
