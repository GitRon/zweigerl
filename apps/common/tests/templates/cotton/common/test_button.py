import pytest

from apps.common.tests.html import parse, render_component


@pytest.mark.parametrize("variant", ["primary", "secondary"])
def test_button_renders_every_variant(variant):
    html = render_component(
        tag=f'<c-common.button variant="{variant}" type="submit" class="w-full">Person anlegen</c-common.button>',
        context={},
    )

    button = parse(html).button
    assert (button.get_text(strip=True), button["type"]) == ("Person anlegen", "submit")


def test_button_with_a_link_target_is_a_link():
    html = render_component(tag='<c-common.button href="/persons/">Personen</c-common.button>', context={})

    soup = parse(html)
    assert soup.button is None
    assert soup.a["href"] == "/persons/"


def test_button_passes_a_datastar_action_through():
    html = render_component(
        tag="<c-common.button data-on:click=\"@post('/persons/')\" disabled>Anlegen</c-common.button>", context={}
    )

    button = parse(html).button
    assert button["data-on:click"] == "@post('/persons/')"
    assert button.has_attr("disabled")
