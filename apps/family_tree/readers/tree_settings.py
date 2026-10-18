from apps.family_tree.models import Person, TreeSettings


def home_person() -> Person | None:
    """
    The person the tree is laid out around, or None while nobody has been chosen.
    """
    tree_settings = TreeSettings.objects.select_related("home_person").filter(pk=TreeSettings.ONLY_ROW).first()
    return tree_settings.home_person if tree_settings else None
