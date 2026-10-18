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
    to "url", so the back button, a reload and a bookmark all land on the same page again.
    """
    response = render(request, template, context)

    if not is_datastar_request(request=request):
        return response

    # The address goes into a script element, so it is written as a JavaScript string literal, and "<"
    # is escaped so that a "</script>" in a query string cannot end the element early.
    url_literal = json.dumps(url).replace("<", "\\u003c")

    return DatastarResponse(
        [
            ServerSentEventGenerator.patch_elements(response.content.decode()),
            ServerSentEventGenerator.execute_script(f"history.pushState(null, '', {url_literal});"),
        ]
    )
