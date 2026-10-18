import pytest

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import SourcesTab
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.source import SourceFactory

TAG = '<c-source.list :sources_tab="sources_tab" />'
LENA = PersonFactory.build(pk=7)


@pytest.mark.django_db
def test_list_shows_each_source_and_the_form_for_a_new_one():
    source = SourceFactory(title="Taufbuch Mariazell")

    html = render_component(tag=TAG, context={"sources_tab": SourcesTab(person=LENA, sources=[source], kinds=[])})

    page = parse(html).find(id="person-card-source-list")
    assert (page.find(id=f"source-{source.pk}").find("h3").get_text(), page.find("summary").get_text()) == (
        "Taufbuch Mariazell",
        "Neue Quelle",
    )


def test_list_without_sources_invites_the_first():
    html = render_component(tag=TAG, context={"sources_tab": SourcesTab(person=LENA, sources=[], kinds=[])})

    assert "Noch keine Quelle da. Leg die erste an." in parse(html).get_text()
