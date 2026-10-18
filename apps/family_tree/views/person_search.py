from datastar_py.django import ServerSentEventGenerator, datastar_response, read_signals
from django.http import HttpRequest
from django_cotton import render_component

from apps.family_tree.readers.person import person_list


@datastar_response
def person_search_view(request: HttpRequest):
    """
    The sidebar's live search (#10): the people matching "$search", patched into the list.
    """
    search = str((read_signals(request) or {}).get("search", "")).strip()
    yield ServerSentEventGenerator.patch_elements(
        render_component(request, "person.list", person_list=person_list(search=search), search=search),
    )
