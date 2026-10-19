from django.http import HttpRequest, HttpResponse
from django.utils.timezone import localdate
from django.views.decorators.http import require_GET

from apps.family_tree.readers.gedcom import gedcom_export

# The media type GEDCOM 7 registered; GEDCOM 5.5.1 never had one of its own.
GEDCOM_CONTENT_TYPE = "text/vnd.familysearch.gedcom; charset=utf-8"


@require_GET
def gedcom_export_view(request: HttpRequest) -> HttpResponse:
    """
    The whole tree as a GEDCOM file to download (#26), named after the day: "zweigerl-2026-10-19.ged". A plain
    download rather than a datastar request - nothing on the page changes.
    """
    response = HttpResponse(gedcom_export(), content_type=GEDCOM_CONTENT_TYPE)
    response["Content-Disposition"] = f'attachment; filename="zweigerl-{localdate().isoformat()}.ged"'
    return response
