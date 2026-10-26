from apps.family_tree.models import Person, Tree


def create_tree(*, name: str) -> Tree:
    """
    Starts a new, empty tree (#34) - for the family of one's partner, say. Raises "ValidationError" with a German
    message for a name that is empty or already taken.
    """
    tree = Tree(name=name.strip())
    # "full_clean" rather than only the constraints "save" checks: it also holds the length of the name.
    tree.full_clean()
    tree.save()
    return tree


def rename_tree(*, tree_id: int, name: str) -> Tree:
    """
    Gives the tree a new name (#34). Raises "Tree.DoesNotExist" for a tree that is not there and "ValidationError"
    with a German message for a name that is empty or already taken.
    """
    tree = Tree.objects.get(pk=tree_id)
    tree.name = name.strip()
    # "full_clean" rather than only the constraints "save" checks: it also holds the length of the name.
    tree.full_clean()
    tree.save()
    return tree


def choose_home_person(*, tree_id: int, person_id: int) -> Tree:
    """
    Makes the person the home person of their tree, whom it is laid out around and relationships are named from
    (#20). Raises "Person.DoesNotExist" for somebody who is not in the tree "tree_id" - deleted in the meantime
    perhaps, or of another tree.
    """
    person = Person.objects.select_related("tree").get(pk=person_id, tree=tree_id)
    tree = person.tree
    tree.home_person = person
    tree.save()
    return tree
