import pytest

from apps.common.tests.html import parse, render_component


@pytest.mark.parametrize("tone", ["ink", "forest", "brick"])
def test_label_renders_every_tone(tone):
    html = render_component(tag=f'<c-common.label text="belegt" tone="{tone}" />', context={})

    assert parse(html).get_text(strip=True) == "belegt"
