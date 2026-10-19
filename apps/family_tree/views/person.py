from datastar_py.django import DatastarResponse, ServerSentEventGenerator, datastar_response
from django.core.exceptions import ValidationError
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django_cotton import render_component

from apps.common.datastar import is_datastar_request, push_url
from apps.common.toasts import toast_sse
from apps.family_tree.actions.person import change_name_and_status
from apps.family_tree.domain.layout import CARD_HEIGHT, CARD_WIDTH
from apps.family_tree.models import Person
from apps.family_tree.readers.person import loose_people, person_card, person_list
from apps.family_tree.readers.tree import tree, tree_card
from apps.family_tree.views.person_search import sidebar_events


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
        {
            "person_list": person_list(search=""),
            "loose_people": loose_people(),
            "tree": tree(),
            "card": card,
            "selection": pk,
        },
    )


@require_POST
@datastar_response
def person_name_view(request: HttpRequest, pk: int):
    """
    Saves the form "Name & Status bearbeiten" in the head of the person card (#30) and patches everything that
    shows the name: the card, closing the form, the sidebar's list under the search still running and its "Lose
    Zweigerl", and the person's card in the tree. A refusal is a toast, and the form stays open with what was entered.
    """
    death_year = request.POST.get("death_year", "").strip()
    if death_year and not death_year.isdecimal():
        yield toast_sse(request=request, text="Das Sterbejahr ist eine Jahreszahl, etwa 1931.", style="error")
        return

    try:
        change_name_and_status(
            person_id=pk,
            given_names=request.POST.get("given_names", ""),
            surname=request.POST.get("surname", ""),
            call_name=request.POST.get("call_name", ""),
            sex=request.POST.get("sex", ""),
            living_status=request.POST.get("living_status", ""),
            death_year=int(death_year) if death_year else None,
        )
    except Person.DoesNotExist:
        yield toast_sse(request=request, text="Diese Person ist nicht mehr im Baum.", style="error")
        return
    except ValidationError as error:
        yield toast_sse(request=request, text=" ".join(error.messages), style="error")
        return

    card = person_card(pk=pk)
    yield ServerSentEventGenerator.patch_elements(render_component(request, "person.card", card=card))
    yield ServerSentEventGenerator.patch_signals({"editing": 0})
    yield from sidebar_events(request, search=request.POST.get("search", "").strip())
    if (in_tree := tree_card(pk=pk)) is not None:
        yield ServerSentEventGenerator.patch_elements(
            render_component(request, "tree.card", card=in_tree, width=CARD_WIDTH, height=CARD_HEIGHT)
        )
    yield toast_sse(request=request, text=f"Passt. {card.entry.name} ist gespeichert.", style="success")
