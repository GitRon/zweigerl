from datastar_py.django import DatastarResponse, ServerSentEventGenerator
from django.http import Http404, HttpRequest
from django_cotton import render_component

from apps.family_tree.readers.person import person_card


def person_card_view(request: HttpRequest, pk: int) -> DatastarResponse:
    """
    The person card of whoever was clicked in the tree (#12), patched beside it. Its own address, answering
    a browser with the whole page, is #13's. Not a generator like the search: a 404 has to be decided before
    the stream starts.
    """
    entry = person_card(pk=pk)
    if entry is None:
        raise Http404
    return DatastarResponse(
        [ServerSentEventGenerator.patch_elements(render_component(request, "person.card", entry=entry))]
    )
