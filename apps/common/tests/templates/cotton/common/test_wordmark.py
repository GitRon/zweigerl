from apps.common.tests.html import parse, render_component


def test_wordmark_is_announced_as_the_name():
    html = render_component(tag='<c-common.wordmark class="text-7xl" />', context={})

    assert parse(html).find(attrs={"role": "img"})["aria-label"] == "Zweigerl"
