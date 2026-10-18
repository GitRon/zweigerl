import pytest

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


def test_toast_session_keeps_every_toast_in_order(request_with_session):
    toast_session(request=request_with_session, text="Angelegt", style="success")
    toast_session(request=request_with_session, text="Datei fehlt", style="error")

    assert request_with_session.session[SESSION_KEY] == [
        {"text": "Angelegt", "style": "success"},
        {"text": "Datei fehlt", "style": "error"},
    ]
