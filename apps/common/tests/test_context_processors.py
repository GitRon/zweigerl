from apps.common.context_processors import toasts
from apps.common.toasts import SESSION_KEY


def test_toasts_hands_over_the_session_toasts_once(request_with_session):
    request_with_session.session[SESSION_KEY] = [{"text": "Angelegt", "style": "success"}]

    context = toasts(request_with_session)

    assert context["toasts"]() == [{"text": "Angelegt", "style": "success"}]
    assert SESSION_KEY not in request_with_session.session


def test_toasts_leaves_the_session_alone_until_the_template_reads_them(request_with_session):
    request_with_session.session[SESSION_KEY] = [{"text": "Angelegt", "style": "success"}]

    toasts(request_with_session)

    assert request_with_session.session[SESSION_KEY] == [{"text": "Angelegt", "style": "success"}]
