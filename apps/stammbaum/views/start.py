from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def start_view(request: HttpRequest) -> HttpResponse:
    """
    The page a visit starts on. Until the tree exists (#11) it only says what Zweigerl is.
    """
    return render(request, "stammbaum/start.html")
