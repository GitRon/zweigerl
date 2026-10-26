from django.urls import reverse

from apps.common.tests.html import parse, render_component

TAG = '<c-gedcom.import-dialog :tree_id="tree_id" />'


def test_import_dialog_opens_itself_and_goes_away_when_closed():
    html = render_component(tag=TAG, context={"tree_id": 3})

    dialog = parse(html).find("dialog")
    assert (dialog["data-init"], dialog["data-on:close"]) == ("el.showModal()", "el.remove()")


def test_import_dialog_reads_the_chosen_file_into_the_preview():
    html = render_component(tag=TAG, context={"tree_id": 3})

    file = parse(html).find("input", attrs={"name": "file"})
    assert file["data-on:change"] == f"@post('{reverse('family_tree:gedcom-preview-view')}', {{contentType: 'form'}})"


def test_import_dialog_imports_the_file_into_the_tree_on_submit():
    html = render_component(tag=TAG, context={"tree_id": 3})

    form = parse(html).find("form")
    assert form["data-on:submit"] == (
        f"@post('{reverse('family_tree:gedcom-import-view', kwargs={'tree_pk': 3})}', {{contentType: 'form'}})"
    )
