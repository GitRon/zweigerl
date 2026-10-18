from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.family_tree.readers.person import person_list


def start_view(request: HttpRequest) -> HttpResponse:
    """
    The page a visit starts on: the sidebar with every person (#10). The tree beside it comes with #11.
    """
    return render(request, "family_tree/start.html", {"person_list": person_list(search="")})
