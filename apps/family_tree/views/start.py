from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.family_tree.readers.person import loose_people, person_list
from apps.family_tree.readers.tree import tree


def start_view(request: HttpRequest) -> HttpResponse:
    """
    The page a visit starts on: the sidebar with every person (#10) and the tree beside it (#12).
    """
    return render(
        request,
        "family_tree/start.html",
        {
            "person_list": person_list(search=""),
            "loose_people": loose_people(),
            "tree": tree(),
            "card": None,
            "selection": 0,
        },
    )
