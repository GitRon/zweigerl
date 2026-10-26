from django.contrib.auth.decorators import login_not_required
from django.http import HttpRequest, HttpResponseRedirect
from django.templatetags.static import static


@login_not_required
def favicon_view(request: HttpRequest) -> HttpResponseRedirect:
    """
    Points "/favicon.ico" at the icon. A page built on the layout links the icon itself; a page that is not,
    Django's admin above all, leaves the browser to ask for "/favicon.ico" instead. Reachable without a login,
    because the browser asks on the login page too. See
    docs/patterns/visual-identity.md, "Word mark and icon".
    """
    # Temporary on purpose: a browser keeps a permanent redirect to a static path for good.
    return HttpResponseRedirect(static("brand/favicon-32.png"))
