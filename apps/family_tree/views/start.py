from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.family_tree.readers.backup import last_backup
from apps.family_tree.readers.person import loose_people, person_list
from apps.family_tree.readers.tree import tree
from apps.family_tree.readers.trees import OpenTree, first_tree_id, open_tree


def start_view(request: HttpRequest) -> HttpResponse:
    """
    Where a visit starts: the first tree (#34) - or, in an installation without one, the page asking for it.
    """
    tree_id = first_tree_id()
    if tree_id is None:
        return render(request, "family_tree/first_tree.html")
    return redirect("family_tree:tree-view", tree_pk=tree_id)


def tree_view(request: HttpRequest, tree_pk: int) -> HttpResponse:
    """
    A tree's page: the sidebar with every person of it (#10) and the tree beside it (#12).
    """
    opened = open_tree(pk=tree_pk)
    if opened is None:
        raise Http404

    return render(
        request,
        "family_tree/start.html",
        {**sidebar_context(opened=opened), "tree": tree(tree_id=tree_pk), "card": None, "selection": 0},
    )


def sidebar_context(*, opened: OpenTree) -> dict:
    """
    What the sidebar of a tree's pages shows: which tree is open and the others (#34), its people (#10), its "Lose
    Zweigerl" (#19) and when the last backup was (#33).
    """
    return {
        "open_tree": opened,
        "person_list": person_list(tree_id=opened.tree.pk, search=""),
        "loose_people": loose_people(tree_id=opened.tree.pk),
        "last_backup": last_backup(),
    }
