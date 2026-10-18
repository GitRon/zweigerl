from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.person import SourcesTab
from apps.family_tree.tests.factories.person import PersonFactory
from apps.family_tree.tests.factories.source import SourceFactory


def test_count_says_how_many_sources_there_are():
    sources = SourceFactory.build_batch(2)

    html = render_component(
        tag='<c-source.count :sources_tab="sources_tab" />',
        context={"sources_tab": SourcesTab(person=PersonFactory.build(pk=7), sources=sources, kinds=[])},
    )

    assert parse(html).find(id="person-card-source-count").get_text() == "2"
