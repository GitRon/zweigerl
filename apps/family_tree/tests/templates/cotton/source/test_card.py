import pytest
from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.source import SourceFactory
from apps.family_tree.tests.factories.source_file import SourceFileFactory

TAG = '<c-source.card :source="source" :person="person" />'


@pytest.mark.django_db
def test_card_shows_kind_title_and_zitat():
    source = SourceFactory(title="Geburtsurkunde Lena", kind="civil_registry", description="Graz, Nr. 3471")

    html = render_component(tag=TAG, context={"source": source, "person": PersonFactory.build(pk=7)})

    card = parse(html).find(id=f"source-{source.pk}")
    assert (card.find("span").get_text(), card.find("h3").get_text(), "Graz, Nr. 3471" in card.get_text()) == (
        "Standesamt",
        "Geburtsurkunde Lena",
        True,
    )


@pytest.mark.django_db
def test_card_links_each_file_to_the_media_view():
    scan = SourceFileFactory(file="sources/3/7.pdf")

    html = render_component(tag=TAG, context={"source": scan.source, "person": PersonFactory.build(pk=7)})

    link = parse(html).find("a", string="Datei 1 · PDF")
    assert (link["href"], link["target"]) == ("/media/sources/3/7.pdf", "_blank")


@pytest.mark.django_db
def test_card_without_files_says_so():
    source = SourceFactory(description="")

    html = render_component(tag=TAG, context={"source": source, "person": PersonFactory.build(pk=7)})

    assert "Noch kein Scan dabei." in parse(html).get_text()


@pytest.mark.django_db
def test_card_attaches_files_to_the_source():
    source = SourceFactory()

    html = render_component(tag=TAG, context={"source": source, "person": PersonFactory.build(pk=7)})

    form = parse(html).find("form")
    url = reverse("family_tree:source-files-view", kwargs={"pk": 7, "source_pk": source.pk})
    assert (form["data-on:submit"], form["enctype"], form.find("input", type="file")["name"]) == (
        f"@post('{url}', {{contentType: 'form'}})",
        "multipart/form-data",
        "files",
    )


@pytest.mark.django_db
def test_card_asks_before_a_file_or_the_source_goes():
    scan = SourceFileFactory()
    source = scan.source

    page = parse(render_component(tag=TAG, context={"source": source, "person": PersonFactory.build(pk=7)}))

    remove_file = page.find("button", attrs={"aria-label": "Datei 1 entfernen"})
    delete_source = page.find("button", string=lambda text: text and text.strip() == "Quelle löschen")
    file_url = reverse("family_tree:delete-source-file-view", kwargs={"pk": 7, "source_pk": source.pk, "file_pk": scan.pk})
    source_url = reverse("family_tree:delete-source-view", kwargs={"pk": 7, "source_pk": source.pk})
    assert (remove_file["data-on:click"], delete_source["data-on:click"]) == (
        f"@get('{file_url}')",
        f"@get('{source_url}')",
    )
