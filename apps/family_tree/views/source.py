from datastar_py.consts import ElementPatchMode
from datastar_py.django import DatastarResponse, ServerSentEventGenerator, datastar_response
from django.core.exceptions import ValidationError
from django.http import Http404, HttpRequest
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from django_cotton import render_component

from apps.common.media import UploadRefusedError
from apps.common.toasts import toast_sse
from apps.family_tree.actions.source import add_source_files, create_source, delete_source, delete_source_file
from apps.family_tree.models import Person, Source, SourceFile
from apps.family_tree.readers.evidence import source_deletion, source_file_deletion
from apps.family_tree.readers.person import sources_tab


@require_POST
@datastar_response
def source_create_view(request: HttpRequest, pk: int):
    """
    Creates a source filed with the person from the form in the Quellen tab of their card (#15), with the scans
    and PDFs chosen there, and patches the tab with it. A refusal keeps the form as it was and says why.
    """
    try:
        source = create_source(
            person_id=pk,
            title=request.POST.get("title", ""),
            kind=request.POST.get("kind", ""),
            description=request.POST.get("description", ""),
            files=request.FILES.getlist("files"),
        )
    except Person.DoesNotExist:
        yield toast_sse(request=request, text="Diese Person ist nicht mehr im Baum.", style="error")
        return
    except ValidationError as error:
        yield toast_sse(request=request, text=" ".join(error.messages), style="error")
        return
    except UploadRefusedError as error:
        yield toast_sse(request=request, text=str(error), style="error")
        return

    yield from _patch_sources_tab(request=request, pk=pk)
    yield toast_sse(request=request, text=f"Passt. „{source.title}“ liegt jetzt bei den Quellen.", style="success")


@require_POST
@datastar_response
def source_files_view(request: HttpRequest, pk: int, source_pk: int):
    """
    Attaches the scans and PDFs chosen on a source's entry in the card of the person "pk" (#15), and patches
    the Quellen tab of that card.
    """
    files = request.FILES.getlist("files")
    if not files:
        yield toast_sse(request=request, text="Such zuerst eine Datei aus.", style="error")
        return

    try:
        add_source_files(source_id=source_pk, files=files)
    except Source.DoesNotExist:
        yield toast_sse(request=request, text="Diese Quelle ist nicht mehr da.", style="error")
        return
    except UploadRefusedError as error:
        yield toast_sse(request=request, text=str(error), style="error")
        return

    yield from _patch_sources_tab(request=request, pk=pk)
    yield toast_sse(request=request, text="Passt. Hängt jetzt an der Quelle.", style="success")


@require_http_methods(["GET", "POST"])
def delete_source_view(request: HttpRequest, pk: int, source_pk: int) -> DatastarResponse:
    """
    "Quelle löschen" on a source in the card of the person "pk" (#72): asked for, it opens a dialog saying what
    goes - or, for a source a fact still cites, which facts do; posted from there, it deletes the source with its
    files, closes the dialog and patches the Quellen tab.
    """
    if request.method == "POST":
        return DatastarResponse(_delete_source(request=request, pk=pk, source_pk=source_pk))

    deletion = source_deletion(source_id=source_pk)
    if deletion is None:
        raise Http404
    return _dialog(
        request=request,
        component="source.delete-dialog",
        deletion=deletion,
        url=reverse("family_tree:delete-source-view", kwargs={"pk": pk, "source_pk": source_pk}),
    )


def _delete_source(*, request: HttpRequest, pk: int, source_pk: int):
    try:
        source = delete_source(source_id=source_pk)
    except Source.DoesNotExist:
        yield toast_sse(request=request, text="Diese Quelle ist nicht mehr da.", style="error")
        return
    except ValidationError as error:
        yield toast_sse(request=request, text=" ".join(error.messages), style="error")
        return

    yield ServerSentEventGenerator.remove_elements(selector="#delete-source-dialog")
    yield from _patch_sources_tab(request=request, pk=pk)
    yield toast_sse(request=request, text=f"Passt. „{source.title}“ ist gelöscht.", style="success")


@require_http_methods(["GET", "POST"])
def delete_source_file_view(request: HttpRequest, pk: int, source_pk: int, file_pk: int) -> DatastarResponse:
    """
    "Datei entfernen" on one scan or PDF of a source in the card of the person "pk" (#72): asked for, it opens a
    dialog naming the file; posted from there, it removes the file, closes the dialog and patches the Quellen tab.
    """
    if request.method == "POST":
        return DatastarResponse(_delete_source_file(request=request, pk=pk, source_pk=source_pk, file_pk=file_pk))

    deletion = source_file_deletion(source_id=source_pk, file_id=file_pk)
    if deletion is None:
        raise Http404
    return _dialog(
        request=request,
        component="source.file-delete-dialog",
        deletion=deletion,
        url=reverse(
            "family_tree:delete-source-file-view", kwargs={"pk": pk, "source_pk": source_pk, "file_pk": file_pk}
        ),
    )


def _delete_source_file(*, request: HttpRequest, pk: int, source_pk: int, file_pk: int):
    try:
        delete_source_file(source_id=source_pk, file_id=file_pk)
    except SourceFile.DoesNotExist:
        yield toast_sse(request=request, text="Diese Datei ist nicht mehr da.", style="error")
        return

    yield ServerSentEventGenerator.remove_elements(selector="#delete-source-file-dialog")
    yield from _patch_sources_tab(request=request, pk=pk)
    yield toast_sse(request=request, text="Passt. Die Datei ist entfernt.", style="success")


def _dialog(*, request: HttpRequest, component: str, **context) -> DatastarResponse:
    return DatastarResponse(
        ServerSentEventGenerator.patch_elements(
            render_component(request, component, **context), mode=ElementPatchMode.APPEND, selector="body"
        )
    )


def _patch_sources_tab(*, request: HttpRequest, pk: int):
    # The list and its count, not the whole card: a morph of the card would put its tabs back the way the server
    # renders them, on the first, while "$tab" still says "sources". The list is replaced rather than morphed,
    # since a morph keeps what was typed into the form and the next source would start with the last one's text.
    found = sources_tab(pk=pk)
    if found is None:
        return
    yield ServerSentEventGenerator.patch_elements(
        render_component(request, "source.list", sources_tab=found), mode=ElementPatchMode.REPLACE
    )
    yield ServerSentEventGenerator.patch_elements(render_component(request, "source.count", sources_tab=found))
