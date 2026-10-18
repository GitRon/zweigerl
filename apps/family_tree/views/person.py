from datastar_py.django import DatastarResponse, ServerSentEventGenerator
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django_cotton import render_component

from apps.common.datastar import is_datastar_request, push_url
from apps.family_tree.readers.person import person_card, person_list
from apps.family_tree.readers.tree import tree


def person_view(request: HttpRequest, pk: int) -> HttpResponse:
    """
    A person's own address (#13): a browser loading it gets the start page with their card open beside the tree,
    a click in the tree only the card, patched in, with the address bar moved along - so a reload or a bookmark
    opens the same card again.
    """
    card = person_card(pk=pk)
    if card is None:
        raise Http404

    if is_datastar_request(request=request):
        return DatastarResponse(
            [
                ServerSentEventGenerator.patch_elements(render_component(request, "person.card", card=card)),
                push_url(url=reverse("family_tree:person-view", kwargs={"pk": pk})),
            ]
        )

    return render(
        request,
        "family_tree/start.html",
        {"person_list": person_list(search=""), "tree": tree(), "card": card, "selection": pk},
    )
