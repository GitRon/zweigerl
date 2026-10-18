import pytest

from apps.common.tests.html import parse, render_component


@pytest.mark.parametrize("style", ["info", "success", "error"])
def test_toast_renders_every_style(style):
    html = render_component(tag=f'<c-common.toast text="Gespeichert" style="{style}" />', context={})

    assert parse(html).get_text(strip=True) == "Gespeichert"


def test_toast_is_announced_to_screen_readers():
    html = render_component(tag='<c-common.toast text="Gespeichert" />', context={})

    assert parse(html).find(attrs={"role": "status"}) is not None
