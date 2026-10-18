from apps.common.tests.html import parse, render_component


def test_layout_places_the_slot_in_the_body():
    html = render_component(tag="<c-common.layout><main>Inhalt</main></c-common.layout>", context={"toasts": []})

    assert parse(html).body.main.get_text() == "Inhalt"


def test_layout_shows_the_toasts_left_in_the_session():
    toasts = [{"text": "Angelegt", "style": "success"}]

    html = render_component(tag="<c-common.layout>Inhalt</c-common.layout>", context={"toasts": toasts})

    assert parse(html).find(id="toasts").get_text(strip=True) == "Angelegt"


def test_layout_names_the_page_before_the_app():
    html = render_component(tag='<c-common.layout title="Personen">Inhalt</c-common.layout>', context={"toasts": []})

    assert parse(html).title.get_text() == "Personen - Zweigerl"


def test_layout_loads_the_vendored_datastar_bundle():
    html = render_component(tag="<c-common.layout>Inhalt</c-common.layout>", context={"toasts": []})

    assert parse(html).find("script", type="module")["src"] == "/static/vendor/datastar/1.0.4/datastar.js"


def test_layout_reloads_the_page_the_back_button_returns_to():
    html = render_component(tag="<c-common.layout>Inhalt</c-common.layout>", context={"toasts": []})

    assert parse(html).body["data-on:popstate__window"] == "window.location.reload()"
