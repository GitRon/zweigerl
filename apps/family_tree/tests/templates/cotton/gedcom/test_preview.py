from dataclasses import replace

from apps.common.tests.html import parse, render_component
from apps.family_tree.domain.gedcom_preview import Preview

TAG = '<c-gedcom.preview :preview="preview" />'
PREVIEW = Preview(
    program="PAF",
    charset="UTF-8",
    people=412,
    families=163,
    sources=2,
    photos_windows=14,
    photos_url=1,
    photos_other=1,
    own_tags=("_MARNM", "_UID"),
    unnamed=1,
    future_dates=1,
    with_contact=3,
    unreadable_dates=8,
)


def test_preview_without_a_file_offers_no_import():
    html = render_component(tag="<c-gedcom.preview />", context={})

    page = parse(html)
    assert [button.get_text(strip=True) for button in page.find_all("button")] == ["Abbrechen"]


def test_preview_names_the_program_it_recognised():
    html = render_component(tag=TAG, context={"preview": PREVIEW})

    assert parse(html).find("h3").get_text() == "Aus PAF erkannt"


def test_preview_of_a_file_without_a_program_says_what_it_found_in_the_file():
    html = render_component(tag=TAG, context={"preview": replace(PREVIEW, program="")})

    assert parse(html).find("h3").get_text() == "In der Datei erkannt"


def test_preview_says_what_the_file_brings_and_what_looks_wrong():
    html = render_component(tag=TAG, context={"preview": PREVIEW})

    text = " ".join(parse(html).get_text().split())
    assert "16 Fotos, 14 mit Windows-Pfad, 1 als URL, 1 mit anderem Pfad" in text
    assert "1 Person ohne Namen" in text and "1 Datum in der Zukunft" in text
    assert "3 Personen mit Adresse oder E-Mail" in text and "8 Daten, die Zweigerl nicht lesen kann" in text


def test_preview_with_nothing_to_warn_about_says_so():
    quiet = replace(PREVIEW, unnamed=0, future_dates=0, with_contact=0, unreadable_dates=0)

    html = render_component(tag=TAG, context={"preview": quiet})

    assert "Nichts." in parse(html).get_text()


def test_preview_offers_the_program_as_the_name_of_the_import():
    html = render_component(tag=TAG, context={"preview": PREVIEW})

    page = parse(html)
    assert page.find("input", attrs={"name": "name"})["value"] == "PAF"
    assert page.find("button", attrs={"type": "submit"})["data-attr:disabled"] == "$importing"
