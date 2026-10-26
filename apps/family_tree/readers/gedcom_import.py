from apps.family_tree.models import Person


def tree_is_empty(*, tree_id: int) -> bool:
    """
    Whether nobody is in the tree "tree_id" yet - the only tree a GEDCOM file is imported into (#22, #25).
    """
    return not Person.objects.filter(tree=tree_id).exists()
