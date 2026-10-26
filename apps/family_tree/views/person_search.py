from datastar_py.django import ServerSentEventGenerator, datastar_response, read_signals
from datastar_py.sse import DatastarEvent
from django.http import HttpRequest
from django_cotton import render_component

from apps.family_tree.readers.person import loose_people, person_list


@datastar_response
def person_search_view(request: HttpRequest, tree_pk: int):
    """
    The sidebar's live search (#10): the people of the tree matching "$search", patched into the list. The tree
    (#12) gets the hits as "$matches" to outline them, and "$filtered" to fade everybody else while a search runs.
    Without a search "$matches" stays empty: datastar sends every signal along with each request.
    """
    yield from search_events(
        request, tree_id=tree_pk, search=str((read_signals(request) or {}).get("search", "")).strip()
    )


def search_events(request: HttpRequest, *, tree_id: int, search: str) -> list[DatastarEvent]:
    """
    The list of the tree "tree_id" patched for "search" and the hits handed to the tree - also sent after a name
    changed (#30), which may move the person in the list or out of the hits.
    """
    found = person_list(tree_id=tree_id, search=search)
    return [
        ServerSentEventGenerator.patch_elements(
            render_component(request, "person.list", person_list=found, search=search),
        ),
        ServerSentEventGenerator.patch_signals(
            {"filtered": bool(search), "matches": [entry.person.pk for entry in found.entries] if search else []}
        ),
    ]


def sidebar_events(request: HttpRequest, *, tree_id: int, search: str) -> list[DatastarEvent]:
    """
    Everything in the sidebar that shows a name or Lebensdaten, patched after one of them changed: the list under
    "search" and the "Lose Zweigerl" (#76), so the next change to a name cannot forget either.
    """
    return [*search_events(request, tree_id=tree_id, search=search), *loose_events(request, tree_id=tree_id)]


def loose_events(request: HttpRequest, *, tree_id: int) -> list[DatastarEvent]:
    """
    The "Lose Zweigerl" patched anew (#76) - after a name changed, or the home person, which leaves others loose.
    """
    return [
        ServerSentEventGenerator.patch_elements(
            render_component(request, "person.loose", loose_people=loose_people(tree_id=tree_id))
        )
    ]
