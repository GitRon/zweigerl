from datastar_py.consts import ElementPatchMode
from datastar_py.django import DatastarResponse, ServerSentEventGenerator, datastar_response
from django.core.exceptions import ValidationError
from django.http import Http404, HttpRequest
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django_cotton import render_component

from apps.common.toasts import toast_sse
from apps.family_tree.actions.fact import change_fact, create_fact, delete_fact
from apps.family_tree.domain.layout import CARD_HEIGHT, CARD_WIDTH
from apps.family_tree.models import Fact, Person
from apps.family_tree.readers.person import FactForm, fact_entry, fact_form, person_card
from apps.family_tree.readers.tree import tree_card
from apps.family_tree.views.person_search import sidebar_events


@require_GET
def new_fact_view(request: HttpRequest, pk: int) -> DatastarResponse:
    """
    The form for a new fact (#14), in place of "Angabe hinzufügen" at the end of the facts on the person card.
    """
    return _form(request=request, form=fact_form(person_id=pk))


@require_POST
@datastar_response
def create_fact_view(request: HttpRequest, pk: int):
    """
    Adds the fact entered in the form on the person card, with the sources it cites, and patches everything
    that shows it. A refusal is a toast, and the form stays open with what was entered.
    """
    try:
        create_fact(person_id=pk, **_fact_fields(request=request))
    except Person.DoesNotExist:
        yield toast_sse(request=request, text="Diese Person ist nicht mehr im Baum.", style="error")
        return
    except ValidationError as error:
        yield toast_sse(request=request, text=" ".join(error.messages), style="error")
        return

    yield from _saved(request=request, pk=pk, text="Passt. Die Angabe ist gespeichert.")


@require_GET
def edit_fact_view(request: HttpRequest, pk: int, fact_pk: int) -> DatastarResponse:
    """
    The form for one fact on the person card (#14), in place of the fact: the two share their id.
    """
    return _form(request=request, form=fact_form(person_id=pk, fact_id=fact_pk))


@require_POST
@datastar_response
def change_fact_view(request: HttpRequest, pk: int, fact_pk: int):
    """
    Saves the fact as changed in its form on the person card and patches everything that shows it; a refusal
    is a toast, and the form stays open.
    """
    try:
        change_fact(person_id=pk, fact_id=fact_pk, **_fact_fields(request=request))
    except Fact.DoesNotExist:
        yield toast_sse(request=request, text="Diese Angabe ist nicht mehr da.", style="error")
        return
    except ValidationError as error:
        yield toast_sse(request=request, text=" ".join(error.messages), style="error")
        return

    yield from _saved(request=request, pk=pk, text="Passt. Die Angabe ist geändert.")


@require_http_methods(["GET", "POST"])
def delete_fact_view(request: HttpRequest, pk: int, fact_pk: int) -> DatastarResponse:
    """
    "Entfernen" in the form of a fact (#14): asked for, it opens a dialog asking whether the fact should really
    go; posted from there, it removes the fact with its citations, closes the dialog and patches the card.
    """
    if request.method == "POST":
        return DatastarResponse(_delete(request=request, pk=pk, fact_pk=fact_pk))

    entry = fact_entry(person_id=pk, fact_id=fact_pk)
    if entry is None:
        raise Http404
    return DatastarResponse(
        ServerSentEventGenerator.patch_elements(
            render_component(
                request,
                "fact.delete-dialog",
                entry=entry,
                url=reverse("family_tree:delete-fact-view", kwargs={"pk": pk, "fact_pk": fact_pk}),
            ),
            mode=ElementPatchMode.APPEND,
            selector="body",
        )
    )


def _delete(*, request: HttpRequest, pk: int, fact_pk: int):
    try:
        delete_fact(person_id=pk, fact_id=fact_pk)
    except Fact.DoesNotExist:
        yield toast_sse(request=request, text="Diese Angabe ist nicht mehr da.", style="error")
        return

    yield ServerSentEventGenerator.remove_elements(selector="#delete-fact-dialog")
    yield from _saved(request=request, pk=pk, text="Passt. Die Angabe ist entfernt.")


def _form(*, request: HttpRequest, form: FactForm | None) -> DatastarResponse:
    if form is None:
        raise Http404
    return DatastarResponse(ServerSentEventGenerator.patch_elements(render_component(request, "fact.form", form=form)))


def _fact_fields(*, request: HttpRequest) -> dict:
    # Each chosen source with the place in it typed beside it, "page_<source id>".
    chosen = [source_id for source_id in request.POST.getlist("sources") if source_id.isdecimal()]
    partner = request.POST.get("partner", "")
    return {
        "kind": request.POST.get("kind", ""),
        "label": request.POST.get("label", ""),
        "value": request.POST.get("value", ""),
        "date": request.POST.get("date", ""),
        "partner_id": int(partner) if partner.isdecimal() else None,
        "reliability": request.POST.get("reliability", Fact.Reliability.DOCUMENTED),
        "citations": {int(source_id): request.POST.get(f"page_{source_id}", "") for source_id in chosen},
    }


def _saved(*, request: HttpRequest, pk: int, text: str):
    # The whole card, closing the form: the facts are its first tab, and a birth or a death changes its head. The
    # Lebensdaten also stand in the sidebar - in its list under the search still running and in its "Lose Zweigerl" -
    # and on the tree's card.
    card = person_card(pk=pk)
    yield ServerSentEventGenerator.patch_elements(render_component(request, "person.card", card=card))
    yield from sidebar_events(request, tree_id=card.entry.person.tree_id, search=request.POST.get("search", "").strip())
    if (in_tree := tree_card(pk=pk)) is not None:
        yield ServerSentEventGenerator.patch_elements(
            render_component(request, "tree.card", card=in_tree, width=CARD_WIDTH, height=CARD_HEIGHT)
        )
    yield toast_sse(request=request, text=text, style="success")
