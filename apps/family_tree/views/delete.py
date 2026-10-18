from datastar_py.consts import ElementPatchMode
from datastar_py.django import DatastarResponse, ServerSentEventGenerator, datastar_response
from django.core.exceptions import ValidationError
from django.http import Http404, HttpRequest
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django_cotton import render_component

from apps.common.toasts import toast_session, toast_sse
from apps.family_tree.actions.person import delete_person, unlink_relative
from apps.family_tree.readers.person import deletion_preview, link_preview


@require_GET
def confirm_delete_person_view(request: HttpRequest, pk: int) -> DatastarResponse:
    """
    The dialog behind "Löschen" on a person's card (#19): what vanishes, what stays, which links go and whom it
    cuts off - or, for the home person, the way to choose another one first.
    """
    preview = deletion_preview(pk=pk)
    if preview is None:
        raise Http404

    return DatastarResponse(
        ServerSentEventGenerator.patch_elements(
            render_component(request, "person.delete-dialog", preview=preview),
            mode=ElementPatchMode.APPEND,
            selector="body",
        )
    )


@require_POST
@datastar_response
def delete_person_view(request: HttpRequest, pk: int):
    """
    Deletes the person once the dialog was confirmed, and goes back to the start page. Whoever the deletion cuts
    off from the home person must have been ticked off - as many as the tick named, so a tree changed in the
    meantime asks again rather than cutting off somebody nobody was told about.
    """
    preview = deletion_preview(pk=pk)
    if preview is None:
        yield toast_sse(request=request, text="Diese Person ist nicht mehr im Baum.", style="error")
        return
    count = len(preview.cut_off)
    if count and request.POST.get("loose_accepted") != str(count):
        people = "hängt 1 Person" if count == 1 else f"hängen {count} Personen"
        yield toast_sse(
            request=request,
            text=f"Ohne {preview.entry.name} {people} lose. Schau's dir im Dialog nochmal an.",
            style="error",
        )
        return

    try:
        delete_person(person_id=pk)
    except ValidationError as error:
        yield toast_sse(request=request, text=" ".join(error.messages), style="error")
        return

    toast_session(request=request, text=f"Passt. {preview.entry.name} ist gelöscht.", style="success")
    yield ServerSentEventGenerator.redirect(reverse("family_tree:start-view"))


@require_GET
def confirm_unlink_view(request: HttpRequest, pk: int, relation: str, relative_pk: int) -> DatastarResponse:
    """
    The short question behind the button of one relative on the Verwandte tab (#19).
    """
    preview = link_preview(pk=pk, relation=relation, relative_pk=relative_pk)
    if preview is None:
        raise Http404

    return DatastarResponse(
        ServerSentEventGenerator.patch_elements(
            render_component(request, "person.unlink-dialog", preview=preview),
            mode=ElementPatchMode.APPEND,
            selector="body",
        )
    )


@require_POST
@datastar_response
def unlink_view(request: HttpRequest, pk: int, relation: str, relative_pk: int):
    """
    Removes the one link and opens the person's card again. A whole page load rather than patches: the tree is laid
    out anew without the link, and who now hangs loose moves to the sidebar.
    """
    preview = link_preview(pk=pk, relation=relation, relative_pk=relative_pk)
    if preview is None:
        yield toast_sse(request=request, text="Diese Verbindung gibt es nicht mehr.", style="error")
        return

    unlink_relative(person_id=pk, relation=relation, relative_id=relative_pk)

    toast_session(
        request=request,
        text=f"Passt. {preview.relative.name} und {preview.person.name} sind nicht mehr verbunden.",
        style="success",
    )
    yield ServerSentEventGenerator.redirect(reverse("family_tree:person-view", kwargs={"pk": pk}))
