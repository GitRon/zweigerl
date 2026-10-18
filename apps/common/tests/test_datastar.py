import pytest
from datastar_py.django import DatastarResponse

from apps.common.datastar import is_datastar_request, push_url, render_page


def test_is_datastar_request_recognises_a_datastar_action(rf):
    request = rf.get("/", headers={"Datastar-Request": "true"})

    assert is_datastar_request(request=request) is True


def test_is_datastar_request_passes_over_plain_navigation(rf):
    request = rf.get("/")

    assert is_datastar_request(request=request) is False


@pytest.mark.django_db
def test_render_page_answers_navigation_with_the_whole_document(request_with_session):
    response = render_page(request=request_with_session, template="common/login_lockout.html", context={}, url="/")

    assert not isinstance(response, DatastarResponse)
    assert response.status_code == 200


@pytest.mark.django_db
def test_render_page_answers_datastar_with_events(datastar_request_with_session):
    response = render_page(
        request=datastar_request_with_session, template="common/login_lockout.html", context={}, url="/"
    )

    assert isinstance(response, DatastarResponse)


@pytest.mark.django_db
def test_render_page_moves_the_address_bar(datastar_request_with_session):
    response = render_page(
        request=datastar_request_with_session, template="common/login_lockout.html", context={}, url="/persons/?q=Huber"
    )

    assert """history.pushState(null, '', "/persons/?q=Huber");""" in b"".join(response.streaming_content).decode()


@pytest.mark.django_db
def test_render_page_keeps_a_query_from_closing_the_script(datastar_request_with_session):
    """
    Reads the response body on purpose, against the rule in the testing strategy: the defect is the
    escaping of the address inside the script element, and nothing but the body shows it.
    """
    response = render_page(
        request=datastar_request_with_session, template="common/login_lockout.html", context={}, url="/?q=</script>"
    )

    body = b"".join(response.streaming_content).decode()
    assert '</script>");' not in body
    assert "\\u003c/script>" in body


@pytest.mark.django_db
def test_render_page_adds_no_history_entry_for_the_page_already_open(datastar_request_with_session):
    response = render_page(
        request=datastar_request_with_session, template="common/login_lockout.html", context={}, url="/"
    )

    assert 'if (location.pathname + location.search !== "/")' in b"".join(response.streaming_content).decode()


def test_push_url_moves_the_address_bar():
    assert """history.pushState(null, '', "/persons/7/");""" in push_url(url="/persons/7/")
