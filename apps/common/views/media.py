import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpRequest, HttpResponse


def media_view(request: HttpRequest, path: str) -> HttpResponse:
    """
    Hands out a photo or a scan - only to someone logged in, which LoginRequiredMiddleware sees to before
    this runs. There is no other way to a media file: MEDIA_URL points here and nothing serves MEDIA_ROOT
    directly. See docs/patterns/data-storage.md, "Photos and scans".
    """
    media_root = Path(settings.MEDIA_ROOT).resolve()
    file_path = (media_root / path).resolve()
    # Resolved first, so neither "../" nor a symlink leads out of the media directory.
    if not file_path.is_relative_to(media_root) or not file_path.is_file():
        raise Http404

    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"

    if settings.ZWEIGERL_MEDIA_ACCEL_PREFIX:
        # Behind nginx (#37): Django has checked the login, nginx sends the bytes from an "internal" location.
        response = HttpResponse(content_type=content_type)
        response["X-Accel-Redirect"] = f"{settings.ZWEIGERL_MEDIA_ACCEL_PREFIX}{file_path.relative_to(media_root)}"
    else:
        response = FileResponse(file_path.open("rb"), content_type=content_type)

    response["Cache-Control"] = "private"
    return response
