from apps.family_tree.tests.factories.source import SourceFactory
from apps.family_tree.tests.factories.source_file import SourceFileFactory


def test_source_file_str_is_its_stored_name():
    assert str(SourceFileFactory.build(file="sources/3/7.pdf")) == "sources/3/7.pdf"


def test_source_file_storage_name_comes_from_the_ids_alone():
    source_file = SourceFileFactory.build(pk=7, source=SourceFactory.build(pk=3))

    assert source_file.storage_name == "sources/3/7"


def test_source_file_format_name_is_the_extension():
    assert SourceFileFactory.build(file="sources/3/7.tif").format_name == "TIF"
