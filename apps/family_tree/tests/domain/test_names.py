import pytest

from apps.family_tree.domain.names import display_name, initials, matches, sort_key


def test_display_name_prefers_the_call_name():
    assert display_name(given_names="Gertrud", surname="Huber", call_name="Gerti") == "Gerti Huber"


def test_display_name_takes_the_first_given_name_without_a_call_name():
    assert display_name(given_names="Johann Georg", surname="Huber", call_name="") == "Johann Huber"


def test_display_name_takes_the_first_of_given_names_separated_by_commas():
    assert display_name(given_names="Maria, Theresia", surname="Huber", call_name="") == "Maria Huber"


def test_display_name_without_a_surname_is_the_first_name_alone():
    assert display_name(given_names="Theresia", surname="", call_name="") == "Theresia"


def test_display_name_of_somebody_nobody_has_named():
    assert display_name(given_names="", surname=" ", call_name="") == "Ohne Namen"


def test_initials_of_first_given_name_and_surname():
    assert initials(given_names="johann Georg", surname="Huber") == "JH"


def test_initials_take_the_first_of_given_names_separated_by_commas():
    assert initials(given_names=",Maria, Theresia", surname="Huber") == "MH"


def test_initials_of_somebody_without_a_name_are_empty():
    assert initials(given_names="", surname="") == ""


def test_sort_key_orders_umlauts_as_their_base_letter():
    names = [("Anna", "Zach"), ("Anna", "Öhler"), ("Anna", "Obermayr")]

    result = sorted(names, key=lambda name: sort_key(given_names=name[0], surname=name[1]))

    assert result == [("Anna", "Obermayr"), ("Anna", "Öhler"), ("Anna", "Zach")]


def test_sort_key_orders_by_given_names_within_a_family_regardless_of_case():
    names = [("josef", "Huber"), ("Anna", "huber")]

    result = sorted(names, key=lambda name: sort_key(given_names=name[0], surname=name[1]))

    assert result == [("Anna", "huber"), ("josef", "Huber")]


def test_sort_key_puts_people_without_a_surname_last():
    names = [("Anna", ""), ("Josef", "Zach")]

    result = sorted(names, key=lambda name: sort_key(given_names=name[0], surname=name[1]))

    assert result == [("Josef", "Zach"), ("Anna", "")]


@pytest.mark.parametrize(
    ("search", "names"),
    [
        ("", ("Lena", "Huber", "")),
        ("lena hub", ("Lena", "Huber", "")),
        ("GERTI", ("Gertrud", "Huber", "Gerti")),
        ("gossl", ("Anna", "Gößl", "")),
        ("Gößl", ("Anna", "Gössl", "")),
        ("öhler", ("Anna", "ÖHLER", "")),
    ],
)
def test_matches_finds_every_word_in_some_name(search, names):
    assert matches(search=search, names=names) is True


def test_matches_needs_every_word():
    assert matches(search="lena brandl", names=("Lena", "Huber", "")) is False
