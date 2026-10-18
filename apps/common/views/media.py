from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.http import FileResponse, Http404, HttpRequest, HttpResponse

# The kinds of file "store_upload" accepts, and the type each is sent as. Nothing else is handed out, so a
# file that reached the media directory some other way - an .html, an .svg - cannot run as a page of
# Zweigerl in the browser of someone logged in.
CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".pdf": "application/pdf",
}


def media_view(request: HttpRequest, path: str) -> HttpResponse:
    """
    Hands out a photo or a scan - only to someone logged in, which LoginRequiredMiddleware sees to before
    this runs. There is no other way to a media file: MEDIA_URL points here and nothing serves MEDIA_ROOT
    directly. See docs/patterns/data-storage.md, "Photos and scans".
    """
    media_root = Path(settings.MEDIA_ROOT).resolve()
    try:
        file_path = (media_root / path).resolve()
    except (ValueError, OSError) as error:
        # A NUL byte or a path the file system refuses is not a file there is.
        raise Http404 from error
    # Resolved first, so neither "../" nor a symlink leads out of the media directory.
    if not file_path.is_relative_to(media_root) or not file_path.is_file():
        raise Http404
    content_type = CONTENT_TYPES.get(file_path.suffix.lower())
    if content_type is None:
        raise Http404

    if settings.ZWEIGERL_MEDIA_ACCEL_PREFIX:
        # Behind nginx (#37): Django has checked the login, nginx sends the bytes from an "internal" location.
        # The header is a URI to nginx, so the path is percent-encoded - a "?" or "#" in a name would
        # otherwise end it early.
        prefix = settings.ZWEIGERL_MEDIA_ACCEL_PREFIX.rstrip("/")
        response = HttpResponse(content_type=content_type)
        response["X-Accel-Redirect"] = f"{prefix}/{quote(file_path.relative_to(media_root).as_posix())}"
    else:
        response = FileResponse(file_path.open("rb"), content_type=content_type)

    # "no-cache": a replaced photo keeps its URL, so the browser asks again rather than showing the old one.
    response["Cache-Control"] = "private, no-cache"
    return response
