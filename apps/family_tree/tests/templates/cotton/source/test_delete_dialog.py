from bs4 import BeautifulSoup
from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.evidence import SourceDeletion
from apps.family_tree.tests.factories.source import SourceFactory

URL = reverse("family_tree:delete-source-view", kwargs={"pk": 7, "source_pk": 3})
TAG = '<c-source.delete-dialog :deletion="deletion" :url="url" />'


def _render(*, file_count: int = 2, citing: list[str] | None = None) -> BeautifulSoup:
    deletion = SourceDeletion(
        source=SourceFactory.build(pk=3, title="Taufbuch"), file_count=file_count, citing=citing or []
    )

    return parse(render_component(tag=TAG, context={"deletion": deletion, "url": URL}))


def test_delete_dialog_says_the_files_go_with_the_source_and_posts_the_deletion():
    page = _render()

    assert (
        " ".join(page.find("p").get_text().split()),
        page.find("form")["data-on:submit"],
    ) == ("Die Quelle verschwindet mitsamt ihren 2 Dateien.", f"@post('{URL}', {{contentType: 'form'}})")


def test_delete_dialog_names_one_file_as_one():
    assert _render(file_count=1).find("p").get_text() == "Die Quelle verschwindet mitsamt ihrer Datei."


def test_delete_dialog_of_a_source_without_files_says_so():
    assert _render(file_count=0).find("p").get_text() == "Die Quelle verschwindet. Eine Datei hängt nicht dran."


def test_delete_dialog_of_a_cited_source_names_the_facts_and_offers_no_deletion():
    page = _render(citing=["Geboren · Lena Huber", "Gestorben · Lena Huber"])

    assert (
        " ".join(page.find("ul").get_text().split()),
        "wären diese Angaben unbelegt" in page.get_text(),
        page.find("form"),
    ) == ("Geboren · Lena Huber Gestorben · Lena Huber", True, None)


def test_delete_dialog_of_a_source_cited_once_speaks_of_one_fact():
    assert "wäre diese Angabe unbelegt" in _render(citing=["Geboren · Lena Huber"]).get_text()
