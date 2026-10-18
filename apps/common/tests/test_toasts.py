import pytest
from django.contrib.sessions.backends.db import SessionStore

from apps.common.toasts import SESSION_KEY, toast_session, toast_sse


@pytest.mark.django_db
def test_toast_sse_appends_the_toast_to_the_toast_area(request_with_session):
    event = toast_sse(request=request_with_session, text="Gespeichert", style="success")

    assert "selector #toasts" in event
    assert "mode append" in event


@pytest.mark.django_db
def test_toast_sse_carries_the_text(request_with_session):
    event = toast_sse(request=request_with_session, text="Gespeichert")

    assert "Gespeichert" in event


@pytest.mark.django_db
def test_toast_session_keeps_every_toast_in_order(request_with_session):
    toast_session(request=request_with_session, text="Angelegt", style="success")
    toast_session(request=request_with_session, text="Datei fehlt", style="error")

    assert request_with_session.session[SESSION_KEY] == [
        {"text": "Angelegt", "style": "success"},
        {"text": "Datei fehlt", "style": "error"},
    ]


@pytest.mark.django_db
def test_toast_session_saves_the_session_itself(request_with_session):
    """
    A streamed datastar response runs after the session middleware has saved the session, so the toast
    has to be stored by the time "toast_session" returns.
    """
    toast_session(request=request_with_session, text="Angelegt", style="success")

    stored = SessionStore(session_key=request_with_session.session.session_key)
    assert stored[SESSION_KEY] == [{"text": "Angelegt", "style": "success"}]
