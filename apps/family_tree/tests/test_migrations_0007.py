"""
The data migration that gives the raw GEDCOM migration 0003 kept the shape of a GEDCOM structure (#26).
Migrations are not measured by the coverage gate, but this one rewrites data the family entered, so it is played
on a real schema, both ways.
"""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.state import StateApps

BEFORE = [("family_tree", "0006_photo")]
AFTER = [("family_tree", "0007_gedcom_raw_as_structures")]

LEGACY = [{"tag": "MARR", "date": "im Krieg"}, {"tag": "_UID", "value": "4F2A"}]
STRUCTURED = [
    {"tag": "MARR", "children": [{"tag": "DATE", "value": "im Krieg"}]},
    {"tag": "_UID", "value": "4F2A"},
]


@pytest.fixture
def couple_before_26(transactional_db):
    """
    The schema as it was before #26, with a couple whose wedding date 0003 could not read - and the latest
    schema again afterwards, so the next test finds the database it expects.
    """
    apps = _apps_at(BEFORE)
    person_model = apps.get_model("family_tree", "Person")
    partnership_model = apps.get_model("family_tree", "Partnership")
    johann, maria = (person_model.objects.create(given_names=name) for name in ("Johann", "Maria"))
    yield partnership_model.objects.create(person_a=johann, person_b=maria, kind="marriage", gedcom_raw=LEGACY)
    MigrationExecutor(connection).migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())


def _apps_at(target: list[tuple[str, str]]) -> StateApps:
    executor = MigrationExecutor(connection)
    executor.migrate(target)
    return executor.loader.project_state(target).apps


def test_migration_turns_a_kept_date_into_a_structure(couple_before_26):
    partnership_model = _apps_at(AFTER).get_model("family_tree", "Partnership")

    partnership = partnership_model.objects.get(pk=couple_before_26.pk)

    assert partnership.gedcom_raw == STRUCTURED


def test_migration_back_restores_the_kept_date(couple_before_26):
    _apps_at(AFTER)
    partnership_model = _apps_at(BEFORE).get_model("family_tree", "Partnership")

    partnership = partnership_model.objects.get(pk=couple_before_26.pk)

    assert partnership.gedcom_raw == LEGACY
