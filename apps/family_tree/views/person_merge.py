from datastar_py.consts import ElementPatchMode
from datastar_py.django import DatastarResponse, ServerSentEventGenerator, datastar_response, read_signals
from django.core.exceptions import ValidationError
from django.http import Http404, HttpRequest
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django_cotton import render_component

from apps.common.toasts import toast_session, toast_sse
from apps.family_tree.actions.person_merge import merge_persons
from apps.family_tree.models import Person
from apps.family_tree.models.person import NAME_AND_STATUS_FIELDS
from apps.family_tree.readers.person import person_entries
from apps.family_tree.readers.person_merge import merge_candidates, merge_preview


@require_GET
def merge_dialog_view(request: HttpRequest, pk: int) -> DatastarResponse:
    """
    The dialog behind "Mit … zusammenführen" on a person's card (#85), searching the tree for the other one.
    """
    entry = person_entries(person_ids=[pk]).get(pk)
    if entry is None:
        raise Http404

    return DatastarResponse(
        ServerSentEventGenerator.patch_elements(
            render_component(request, "person.merge-dialog", entry=entry), mode=ElementPatchMode.APPEND, selector="body"
        )
    )


@require_GET
@datastar_response
def merge_candidates_view(request: HttpRequest, pk: int):
    """
    Whom the dialog offers to merge with the person, for "$merge_search", patched into its list.
    """
    signals = read_signals(request) or {}
    search = str(signals.get("merge_search", "")).strip()
    yield ServerSentEventGenerator.patch_elements(
        render_component(
            request, "person.merge-candidates", candidates=merge_candidates(pk=pk, search=search), pk=pk, search=search
        )
    )


@require_GET
def merge_compare_view(request: HttpRequest, pk: int, other_pk: int) -> DatastarResponse:
    """
    The two side by side in place of the search, asking which name, sex and status the person keeps and saying that
    the merge cannot be undone - or why the two cannot be one.
    """
    preview = merge_preview(pk=pk, other_pk=other_pk)
    if preview is None:
        raise Http404

    return DatastarResponse(
        ServerSentEventGenerator.patch_elements(render_component(request, "person.merge-compare", preview=preview))
    )


@require_POST
@datastar_response
def merge_view(request: HttpRequest, pk: int, other_pk: int):
    """
    Merges the other one into the person once the comparison was confirmed, taking each field chosen as "other"
    from them, and opens the person's card. A whole page load: the tree, the list and the Lose Zweigerl all lose
    somebody. A merge the family's rules refuse leaves the dialog open with the reason as a toast.
    """
    from_other = [name for name in NAME_AND_STATUS_FIELDS if request.POST.get(name) == "other"]
    try:
        merge_persons(person_id=pk, other_id=other_pk, from_other=from_other)
    except Person.DoesNotExist:
        yield toast_sse(request=request, text="Eine der beiden ist nicht mehr im Baum.", style="error")
        return
    except ValidationError as error:
        yield toast_sse(request=request, text=" ".join(error.messages), style="error")
        return

    name = person_entries(person_ids=[pk])[pk].name
    toast_session(request=request, text=f"Passt. Jetzt gibt's {name} nur noch einmal.", style="success")
    yield ServerSentEventGenerator.redirect(reverse("family_tree:person-view", kwargs={"pk": pk}))
