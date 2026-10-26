from datastar_py.consts import ElementPatchMode
from datastar_py.django import DatastarResponse, ServerSentEventGenerator, datastar_response
from django.core.exceptions import ValidationError
from django.http import Http404, HttpRequest
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from django_cotton import render_component

from apps.common.toasts import toast_sse
from apps.family_tree.actions.note import change_note, create_note, delete_note
from apps.family_tree.models import Note, Person
from apps.family_tree.readers.person import note_entry, notes_tab


@require_POST
@datastar_response
def note_create_view(request: HttpRequest, pk: int):
    """
    Writes the note entered in the Notizen tab of the person card (#17), signed by whoever is logged in, and
    patches the tab. A refusal keeps the form as it was and says why.
    """
    try:
        create_note(person_id=pk, author_id=request.user.pk, text=request.POST.get("text", ""))
    except Person.DoesNotExist:
        yield toast_sse(request=request, text="Diese Person ist nicht mehr im Baum.", style="error")
        return
    except ValidationError as error:
        yield toast_sse(request=request, text=" ".join(error.messages), style="error")
        return

    yield from _patch_notes_tab(request=request, pk=pk)
    yield toast_sse(request=request, text="Passt. Die Notiz steht da.", style="success")


@require_POST
@datastar_response
def note_change_view(request: HttpRequest, pk: int, note_pk: int):
    """
    Saves a note on the card of the person "pk" as changed in its form (#17) and patches the Notizen tab; a
    refusal is a toast, and the form stays open.
    """
    try:
        change_note(person_id=pk, note_id=note_pk, text=request.POST.get("text", ""))
    except Note.DoesNotExist:
        yield toast_sse(request=request, text="Diese Notiz ist nicht mehr da.", style="error")
        return
    except ValidationError as error:
        yield toast_sse(request=request, text=" ".join(error.messages), style="error")
        return

    yield from _patch_notes_tab(request=request, pk=pk)
    yield toast_sse(request=request, text="Passt. Die Notiz ist geändert.", style="success")


@require_http_methods(["GET", "POST"])
def delete_note_view(request: HttpRequest, pk: int, note_pk: int) -> DatastarResponse:
    """
    "Löschen" on a note in the card of the person "pk" (#17): asked for, it opens a dialog showing the note;
    posted from there, it deletes the note, closes the dialog and patches the Notizen tab.
    """
    if request.method == "POST":
        return DatastarResponse(_delete_note(request=request, pk=pk, note_pk=note_pk))

    entry = note_entry(person_id=pk, note_id=note_pk)
    if entry is None:
        raise Http404
    return DatastarResponse(
        ServerSentEventGenerator.patch_elements(
            render_component(
                request,
                "note.delete-dialog",
                entry=entry,
                url=reverse("family_tree:delete-note-view", kwargs={"pk": pk, "note_pk": note_pk}),
            ),
            mode=ElementPatchMode.APPEND,
            selector="body",
        )
    )


def _delete_note(*, request: HttpRequest, pk: int, note_pk: int):
    try:
        delete_note(person_id=pk, note_id=note_pk)
    except Note.DoesNotExist:
        yield toast_sse(request=request, text="Diese Notiz ist nicht mehr da.", style="error")
        return

    yield ServerSentEventGenerator.remove_elements(selector="#delete-note-dialog")
    yield from _patch_notes_tab(request=request, pk=pk)
    yield toast_sse(request=request, text="Passt. Die Notiz ist gelöscht.", style="success")


def _patch_notes_tab(*, request: HttpRequest, pk: int):
    # The list and its count, not the whole card, which would morph its tabs back to the first. The list is
    # replaced rather than morphed, so the form for a new note starts empty and no note stays open for editing.
    # Every caller has just found the person through one of their notes or written one, so they are there.
    found = notes_tab(pk=pk)
    yield ServerSentEventGenerator.patch_elements(
        render_component(request, "note.list", notes_tab=found), mode=ElementPatchMode.REPLACE
    )
    yield ServerSentEventGenerator.patch_elements(render_component(request, "note.count", notes_tab=found))
