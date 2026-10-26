from datastar_py.consts import ElementPatchMode
from datastar_py.django import ServerSentEventGenerator, datastar_response
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django_cotton import render_component

from apps.common.toasts import toast_session, toast_sse
from apps.family_tree.actions.gedcom_import import ImportRefusedError, import_gedcom
from apps.family_tree.domain.gedcom_preview import Preview, UnreadableGedcomError, preview_file
from apps.family_tree.models import Tree


@require_GET
@datastar_response
def gedcom_import_dialog_view(request: HttpRequest, tree_pk: int):
    """
    The dialog behind "GEDCOM importieren" on the settings page of a tree (#25), asking for the file.
    """
    yield ServerSentEventGenerator.patch_elements(
        render_component(request, "gedcom.import-dialog", tree_id=tree_pk),
        mode=ElementPatchMode.APPEND,
        selector="body",
    )


@require_POST
@datastar_response
def gedcom_preview_view(request: HttpRequest):
    """
    Reads the file chosen in the dialog without saving anything and shows what it would bring (#25). A file
    that is no GEDCOM empties the preview, so nothing can be imported from it, and says why.
    """
    file = request.FILES.get("file")
    if file is None:
        yield _preview(request=request, preview=None)
        yield toast_sse(request=request, text="Such zuerst eine GEDCOM-Datei aus.", style="error")
        return

    try:
        preview = preview_file(file=file, today=timezone.localdate())
    except UnreadableGedcomError as error:
        yield _preview(request=request, preview=None)
        yield toast_sse(request=request, text=str(error), style="error")
        return

    yield _preview(request=request, preview=preview)


@require_POST
@datastar_response
def gedcom_import_view(request: HttpRequest, tree_pk: int):
    """
    "Importieren" in the dialog (#25): the same import as "manage.py import_gedcom", into the tree whose settings it
    was opened from, from the file the preview was read from - the browser sends it again, so nothing waits on disk
    in between. Leads to the tree, which now has everybody in it. A refusal leaves the dialog open and says why.
    """
    file = request.FILES.get("file")
    if file is None:
        yield toast_sse(request=request, text="Such zuerst eine GEDCOM-Datei aus.", style="error")
        return

    try:
        result = import_gedcom(tree_id=tree_pk, file=file, name=request.POST.get("name", ""))
    except Tree.DoesNotExist:
        yield toast_sse(request=request, text="Diesen Stammbaum gibt es nicht mehr.", style="error")
        return
    except ImportRefusedError as error:
        yield toast_sse(request=request, text=str(error), style="error")
        return

    toast_session(request=request, text=f"Passt. „{result.gedcom_import.name}“ ist importiert.", style="success")
    yield ServerSentEventGenerator.redirect(reverse("family_tree:tree-view", kwargs={"tree_pk": tree_pk}))


def _preview(*, request: HttpRequest, preview: Preview | None):
    return ServerSentEventGenerator.patch_elements(render_component(request, "gedcom.preview", preview=preview))
