from apps.common.tests.html import parse, render_component


def test_file_field_passes_the_form_and_datastar_attributes_to_the_input():
    html = render_component(
        tag=(
            '<c-common.file-field name="files" multiple required accept=".pdf" class="mt-2" '
            "data-on:change=\"@post('/preview/')\" />"
        ),
        context={},
    )

    field = parse(html).find("input")
    assert (field["type"], field["name"], field["accept"], field["data-on:change"]) == (
        "file",
        "files",
        ".pdf",
        "@post('/preview/')",
    )
    assert field.has_attr("multiple") and field.has_attr("required")
