"""
The data migration that puts everything already entered into one tree (#34). Migrations are not measured by the
coverage gate, but this one moves the data the family entered, so it is played on a real schema, both ways.
"""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.state import StateApps

BEFORE = [("family_tree", "0011_note")]
AFTER = [("family_tree", "0012_tree")]


@pytest.fixture
def family_before_34(transactional_db):
    """
    The schema as it was before #34, with a person, a source, a photo, an import and the home person in the
    settings - and the latest schema again afterwards, so the next test finds the database it expects.
    """
    apps = _apps_at(BEFORE)
    origin = apps.get_model("family_tree", "GedcomImport").objects.create(name="PAF Huber")
    lena = apps.get_model("family_tree", "Person").objects.create(given_names="Lena", gedcom_import=origin)
    apps.get_model("family_tree", "Source").objects.create(title="Taufbuch Mariazell")
    apps.get_model("family_tree", "Photo").objects.create(file="photos/1/original.jpg")
    apps.get_model("family_tree", "TreeSettings").objects.create(pk=1, home_person=lena)
    yield lena
    _apps_at(MigrationExecutor(connection).loader.graph.leaf_nodes())


@pytest.fixture
def nothing_before_34(transactional_db):
    """
    An installation that never had anything in it, at the schema before #34.
    """
    _apps_at(BEFORE)
    yield
    _apps_at(MigrationExecutor(connection).loader.graph.leaf_nodes())


def _apps_at(target: list[tuple[str, str]]) -> StateApps:
    executor = MigrationExecutor(connection)
    executor.migrate(target)
    return executor.loader.project_state(target).apps


def test_migration_puts_everything_into_one_tree_with_the_home_person(family_before_34):
    apps = _apps_at(AFTER)

    tree = apps.get_model("family_tree", "Tree").objects.get()

    assert (tree.name, tree.home_person_id) == ("Stammbaum", family_before_34.pk)
    assert (
        list(apps.get_model("family_tree", "Person").objects.values_list("tree", flat=True)),
        list(apps.get_model("family_tree", "Source").objects.values_list("tree", flat=True)),
        list(apps.get_model("family_tree", "Photo").objects.values_list("tree", flat=True)),
        list(apps.get_model("family_tree", "GedcomImport").objects.values_list("tree", flat=True)),
    ) == ([tree.pk], [tree.pk], [tree.pk], [tree.pk])


def test_migration_gives_an_empty_installation_no_tree(nothing_before_34):
    apps = _apps_at(AFTER)

    assert apps.get_model("family_tree", "Tree").objects.exists() is False


def test_migration_back_restores_the_home_person_in_the_settings(family_before_34):
    _apps_at(AFTER)
    apps = _apps_at(BEFORE)

    assert apps.get_model("family_tree", "TreeSettings").objects.get().home_person_id == family_before_34.pk
