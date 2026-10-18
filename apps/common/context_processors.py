from django.http import HttpRequest

from apps.common.toasts import SESSION_KEY


def toasts(request: HttpRequest) -> dict:
    """
    Hands the layout the toasts a previous request left in the session, and forgets them, so each one is
    shown exactly once.

    A callable rather than the list: the template calls it only where it reads "toasts", which is the
    layout. Every fragment a datastar response renders goes through the context processors as well, and
    popping there would throw away the toasts a redirect is about to show.
    """

    def pop() -> list[dict]:
        return request.session.pop(SESSION_KEY, [])

    return {"toasts": pop}
