from dataclasses import dataclass

from apps.family_tree.models import Person, Tree


@dataclass(frozen=True, kw_only=True)
class OpenTree:
    tree: Tree
    # The other trees of the installation, to switch to (#34) - empty while there is only this one.
    others: list[Tree]


def open_tree(*, pk: int) -> OpenTree | None:
    """
    The tree a page shows, with the others beside it for the sidebar - or None for a tree that is not there.
    """
    trees = list(Tree.objects.all())
    tree = next((tree for tree in trees if tree.pk == pk), None)
    if tree is None:
        return None
    return OpenTree(tree=tree, others=[other for other in trees if other.pk != pk])


def first_tree_id() -> int | None:
    """
    The tree "/" opens: the first by name - or None in an installation without one, which asks for it.
    """
    return Tree.objects.values_list("pk", flat=True).first()


def home_person(*, tree_id: int) -> Person | None:
    """
    The person the tree "tree_id" is laid out around, or None while nobody has been chosen.
    """
    tree = Tree.objects.select_related("home_person").filter(pk=tree_id).first()
    return tree.home_person if tree else None


def tree_id_by_name(*, name: str) -> int | None:
    """
    The tree called "name", for "manage.py import_gedcom --tree" - or None while there is none of that name.
    """
    return Tree.objects.filter(name=name).values_list("pk", flat=True).first()
