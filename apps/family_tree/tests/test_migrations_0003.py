"""
The data migration that turns Partnership.start and .end into facts (#8). Migrations are not measured
by the coverage gate, but this one rewrites data the family entered, so it is played on a real schema, both
ways.
"""

import datetime

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.state import StateApps

BEFORE = [("family_tree", "0002_facts_sources_citations")]
AFTER = [("family_tree", "0004_remove_partnership_start_end")]


@pytest.fixture
def couples_before_8(transactional_db):
    """
    The schema as it was before #8, with three couples in it - and the latest schema again afterwards, so
    the next test finds the database it expects.
    """
    executor = MigrationExecutor(connection)
    executor.migrate(BEFORE)
    apps = executor.loader.project_state(BEFORE).apps
    person_model = apps.get_model("family_tree", "Person")
    partnership_model = apps.get_model("family_tree", "Partnership")
    johann, maria, franz, gerti = (
        person_model.objects.create(given_names=name) for name in ("Johann", "Maria", "Franz", "Gerti")
    )
    couples = {
        "marriage": partnership_model.objects.create(
            person_a=johann, person_b=maria, kind="marriage", start="1985", end="ABT 2001"
        ),
        "cohabitation": partnership_model.objects.create(
            person_a=franz, person_b=gerti, kind="cohabitation", start="BET 1990 AND 1992"
        ),
        "unreadable": partnership_model.objects.create(
            person_a=johann, person_b=franz, kind="marriage", start="im Krieg"
        ),
    }
    yield couples
    MigrationExecutor(connection).migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())


def _apps_at(target: list[tuple[str, str]]) -> StateApps:
    executor = MigrationExecutor(connection)
    executor.migrate(target)
    return executor.loader.project_state(target).apps


def test_migration_turns_a_marriage_into_marriage_and_divorce(couples_before_8):
    fact_model = _apps_at(AFTER).get_model("family_tree", "Fact")

    facts = set(
        fact_model.objects.filter(partnership_id=couples_before_8["marriage"].pk).values_list(
            "kind", "date_kind", "date_1", "precision"
        )
    )

    assert facts == {
        ("marriage", "exact", datetime.date(1985, 1, 1), "year"),
        ("divorce", "about", datetime.date(2001, 1, 1), "year"),
    }


def test_migration_keeps_the_start_of_any_other_couple_as_its_own_fact(couples_before_8):
    fact_model = _apps_at(AFTER).get_model("family_tree", "Fact")

    fact = fact_model.objects.get(partnership_id=couples_before_8["cohabitation"].pk)

    assert (fact.kind, fact.label, fact.date_2, fact.sort_date) == (
        "custom",
        "Beginn der Partnerschaft",
        datetime.date(1992, 1, 1),
        datetime.date(1991, 7, 2),
    )


def test_migration_keeps_an_unreadable_date_raw(couples_before_8):
    partnership_model = _apps_at(AFTER).get_model("family_tree", "Partnership")

    raw = partnership_model.objects.get(pk=couples_before_8["unreadable"].pk).gedcom_raw

    assert raw == [{"tag": "MARR", "date": "im Krieg"}]


def test_migration_back_writes_the_dates_into_start_and_end_again(couples_before_8):
    _apps_at(AFTER)
    partnership_model = _apps_at(BEFORE).get_model("family_tree", "Partnership")

    texts = set(partnership_model.objects.exclude(start="", end="").values_list("start", "end"))

    assert texts == {("1985", "ABT 2001"), ("BET 1990 AND 1992", "")}
