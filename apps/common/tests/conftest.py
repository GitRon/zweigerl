import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.http import HttpRequest


@pytest.fixture
def request_with_session(rf) -> HttpRequest:
    """
    A request carrying an empty session, as the session middleware would leave it.
    """
    request = rf.get("/")
    request.session = SessionStore()

    return request


@pytest.fixture
def datastar_request_with_session(rf) -> HttpRequest:
    """
    The same, as sent by a datastar action rather than by the browser navigating.
    """
    request = rf.get("/", headers={"Datastar-Request": "true"})
    request.session = SessionStore()

    return request
