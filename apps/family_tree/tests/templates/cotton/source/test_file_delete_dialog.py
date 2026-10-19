import pytest
from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.evidence import SourceFileDeletion
from apps.family_tree.tests.factories.source_file import SourceFileFactory

TAG = '<c-source.file-delete-dialog :deletion="deletion" :url="url" />'


@pytest.mark.django_db
def test_file_delete_dialog_names_the_file_and_posts_the_removal():
    scan = SourceFileFactory(source__title="Taufbuch", file="sources/3/7.pdf")
    url = reverse("family_tree:delete-source-file-view", kwargs={"pk": 7, "source_pk": scan.source.pk, "file_pk": scan.pk})

    page = parse(
        render_component(tag=TAG, context={"deletion": SourceFileDeletion(source_file=scan, number=2), "url": url})
    )

    assert (page.find("p").get_text(), page.find("form")["data-on:submit"]) == (
        "Datei 2 · PDF von „Taufbuch“",
        f"@post('{url}', {{contentType: 'form'}})",
    )
