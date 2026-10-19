from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import PhotosTab
from apps.family_tree.tests.factories.person import PersonFactory


def test_count_says_how_many_photos_there_are():
    html = render_component(
        tag='<c-photo.count :photos_tab="photos_tab" />',
        context={"photos_tab": PhotosTab(person=PersonFactory.build(pk=7), photos=[])},
    )

    assert parse(html).find(id="person-card-photo-count").get_text() == "0"
