import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.family_tree.models import GedcomImport
from apps.family_tree.tests.factories.gedcom_import import GedcomImportFactory
from apps.family_tree.tests.factories.tree import TreeFactory


def test_gedcom_import_str_is_its_name():
    assert str(GedcomImportFactory.build(name="PAF Huber")) == "PAF Huber"


@pytest.mark.django_db
def test_gedcom_import_refuses_a_missing_name_on_save():
    with pytest.raises(ValidationError, match="Ein Import braucht einen Namen"):
        GedcomImportFactory(name="")


@pytest.mark.django_db
def test_gedcom_import_refuses_a_missing_name_in_the_database():
    with pytest.raises(IntegrityError, match="gedcomimport_has_name"):
        GedcomImport.objects.bulk_create([GedcomImportFactory.build(tree=TreeFactory(), name="")])
