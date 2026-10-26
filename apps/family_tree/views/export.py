from django.http import Http404, HttpRequest, HttpResponse
from django.utils.timezone import localdate
from django.views.decorators.http import require_GET

from apps.family_tree.domain.file_names import file_slug
from apps.family_tree.readers.gedcom import gedcom_export
from apps.family_tree.readers.trees import open_tree

# The media type GEDCOM 7 registered; GEDCOM 5.5.1 never had one of its own.
GEDCOM_CONTENT_TYPE = "text/vnd.familysearch.gedcom; charset=utf-8"


@require_GET
def gedcom_export_view(request: HttpRequest, tree_pk: int) -> HttpResponse:
    """
    The tree as a GEDCOM file to download (#26, #34), named after the tree and the day:
    "zweigerl-familie-huber-2026-10-19.ged". A plain download rather than a datastar request - nothing on the page
    changes.
    """
    opened = open_tree(pk=tree_pk)
    if opened is None:
        raise Http404

    response = HttpResponse(gedcom_export(tree_id=tree_pk), content_type=GEDCOM_CONTENT_TYPE)
    name = file_slug(text=opened.tree.name)
    response["Content-Disposition"] = f'attachment; filename="zweigerl-{name}-{localdate().isoformat()}.ged"'
    return response
