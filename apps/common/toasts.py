"""
Short confirmations in the corner of the page, the same on every screen.

Two ways to the same toast, depending on whether the response stays on the page - see
docs/patterns/datastar.md, "Toasts".
"""

from typing import Literal

from datastar_py.consts import ElementPatchMode
from datastar_py.django import ServerSentEventGenerator
from datastar_py.sse import DatastarEvent
from django.http import HttpRequest
from django_cotton import render_component

ToastStyle = Literal["info", "success", "error"]

SESSION_KEY = "_toasts"


def toast_sse(*, request: HttpRequest, text: str, style: ToastStyle = "info") -> DatastarEvent:
    """
    The toast as an event of a datastar response, appended to the toast area of the page already open.
    """
    return ServerSentEventGenerator.patch_elements(
        render_component(request, "common.toast", text=text, style=style),
        mode=ElementPatchMode.APPEND,
        selector="#toasts",
    )


def toast_session(*, request: HttpRequest, text: str, style: ToastStyle = "info") -> None:
    """
    The toast for the page a redirect leads to, kept in the session until the layout renders it.
    """
    request.session[SESSION_KEY] = [*request.session.get(SESSION_KEY, []), {"text": str(text), "style": style}]
