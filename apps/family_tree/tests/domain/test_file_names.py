import pytest

from apps.family_tree.domain.file_names import file_slug


@pytest.mark.parametrize(
    ("text", "slug"),
    [
        ("Familie Huber", "familie-huber"),
        ("Familie Gößl", "familie-goessl"),
        ("Müller & Öhler", "mueller-oehler"),
        ("Dvořák", "dvorak"),
        ("  -Huber-  ", "huber"),
    ],
)
def test_file_slug_spells_the_name_for_a_file(text, slug):
    assert file_slug(text=text) == slug


def test_file_slug_of_a_name_with_nothing_left_is_the_fallback():
    assert file_slug(text="Ахнен") == "stammbaum"
