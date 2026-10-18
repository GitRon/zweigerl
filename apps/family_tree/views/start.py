from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def start_view(request: HttpRequest) -> HttpResponse:
    """
    The page a visit starts on. Until the tree is drawn (#12) it only says what Zweigerl is.
    """
    return render(request, "family_tree/start.html")
