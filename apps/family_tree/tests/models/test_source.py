import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.family_tree.models import Source
from apps.family_tree.tests.factories.source import SourceFactory
from apps.family_tree.tests.factories.tree import TreeFactory


def test_source_str_is_its_title():
    assert str(SourceFactory.build(title="Geburtsurkunde")) == "Geburtsurkunde"


@pytest.mark.django_db
def test_source_refuses_a_missing_title_on_save():
    with pytest.raises(ValidationError, match="Eine Quelle braucht einen Titel"):
        SourceFactory(title="")


@pytest.mark.django_db
def test_source_refuses_a_missing_title_in_the_database():
    with pytest.raises(IntegrityError, match="source_has_title"):
        Source.objects.bulk_create([SourceFactory.build(tree=TreeFactory(), title="")])


@pytest.mark.django_db
def test_source_refuses_an_unknown_kind_on_save():
    with pytest.raises(ValidationError, match="Diese Art von Quelle kennt Zweigerl nicht"):
        SourceFactory(kind="rumour")


@pytest.mark.django_db
def test_source_refuses_an_unknown_kind_in_the_database():
    with pytest.raises(IntegrityError, match="source_kind_valid"):
        Source.objects.bulk_create([SourceFactory.build(tree=TreeFactory(), kind="rumour")])
