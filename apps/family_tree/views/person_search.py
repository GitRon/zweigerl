from datastar_py.django import ServerSentEventGenerator, datastar_response, read_signals
from django.http import HttpRequest
from django_cotton import render_component

from apps.family_tree.readers.person import person_list


@datastar_response
def person_search_view(request: HttpRequest):
    """
    The sidebar's live search (#10): the people matching "$search", patched into the list. The tree (#12)
    gets the hits as "$matches" to outline them, and "$filtered" to fade everybody else while a search runs.
    Without a search "$matches" stays empty: datastar sends every signal along with each request.
    """
    search = str((read_signals(request) or {}).get("search", "")).strip()
    found = person_list(search=search)
    yield ServerSentEventGenerator.patch_elements(
        render_component(request, "person.list", person_list=found, search=search),
    )
    yield ServerSentEventGenerator.patch_signals(
        {"filtered": bool(search), "matches": [entry.person.pk for entry in found.entries] if search else []}
    )
