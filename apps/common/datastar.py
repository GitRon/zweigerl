"""
The two answers a page can give: the whole document to a browser that navigates to it, and the same
document as one datastar event to a page that asks for it. See docs/patterns/datastar.md, "Pages".
"""

import json

from datastar_py.django import DatastarResponse, ServerSentEventGenerator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def is_datastar_request(*, request: HttpRequest) -> bool:
    """
    Whether the request came from a datastar action ("@get", "@post", ...) rather than from the browser
    navigating. datastar sets the header on every request it makes.
    """
    return "Datastar-Request" in request.headers


def render_page(*, request: HttpRequest, template: str, context: dict, url: str) -> HttpResponse:
    """
    Renders a page whole, or - asked by datastar - morphs it into the open one and moves the address bar
    to "url", so a reload and a bookmark land on the same page again. The back button reloads the address
    it goes back to, see the layout.
    """
    response = render(request, template, context)

    if not is_datastar_request(request=request):
        return response

    return DatastarResponse([ServerSentEventGenerator.patch_elements(response.content.decode()), push_url(url=url)])


def push_url(*, url: str) -> str:
    """
    The event that moves the address bar to "url" without loading it, for a datastar answer that stands for a
    page of its own - see docs/patterns/datastar.md, "Pages".
    """
    # The address goes into a script element, so it is written as a JavaScript string literal, and "<"
    # is escaped so that a "</script>" in a query string cannot end the element early. A request for the
    # page already open adds no history entry, so the back button does not have to be pressed twice.
    url_literal = json.dumps(url).replace("<", "\\u003c")
    return ServerSentEventGenerator.execute_script(
        f"if (location.pathname + location.search !== {url_literal}) history.pushState(null, '', {url_literal});"
    )
