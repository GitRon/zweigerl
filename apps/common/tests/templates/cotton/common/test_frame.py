from apps.common.tests.html import parse, render_component


def test_frame_shows_the_photo_with_its_description():
    html = render_component(
        tag='<c-common.frame src="/media/foto.jpg" alt="Hochzeit 1951" initials="MM" class="w-14" />', context={}
    )

    image = parse(html).find("img")
    assert (image["src"], image["alt"]) == ("/media/foto.jpg", "Hochzeit 1951")


def test_frame_without_a_photo_shows_the_initials():
    html = render_component(tag='<c-common.frame initials="MM" />', context={})

    soup = parse(html)
    assert soup.find("img") is None
    assert soup.get_text(strip=True) == "MM"


def test_frame_without_photo_or_initials_asks_for_a_photo():
    html = render_component(tag="<c-common.frame />", context={})

    assert parse(html).get_text(strip=True) == "Foto"


def test_frame_without_a_photo_is_left_to_the_name_beside_it():
    html = render_component(tag='<c-common.frame initials="MM" />', context={})

    assert parse(html).span["aria-hidden"] == "true"
