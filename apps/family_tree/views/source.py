from datastar_py.consts import ElementPatchMode
from datastar_py.django import ServerSentEventGenerator, datastar_response
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.views.decorators.http import require_POST
from django_cotton import render_component

from apps.common.media import UploadRefusedError
from apps.common.toasts import toast_sse
from apps.family_tree.actions.source import add_source_files, create_source
from apps.family_tree.models import Person, Source
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
