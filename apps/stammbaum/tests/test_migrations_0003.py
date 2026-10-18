"""
The data migration that turns Partnerschaft.beginn and .ende into Angaben (#8). Migrations are not measured
by the coverage gate, but this one rewrites data the family entered, so it is played on a real schema, both
ways.
"""

import datetime

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.state import StateApps

VORHER = [("stammbaum", "0002_angaben_quellen_zitate")]
NACHHER = [("stammbaum", "0004_remove_partnerschaft_beginn_ende")]


@pytest.fixture
def paare_vor_8(transactional_db):
    """
    The schema as it was before #8, with three couples in it - and the latest schema again afterwards, so
    the next test finds the database it expects.
    """
    executor = MigrationExecutor(connection)
    executor.migrate(VORHER)
    apps = executor.loader.project_state(VORHER).apps
    person_model = apps.get_model("stammbaum", "Person")
    partnerschaft_model = apps.get_model("stammbaum", "Partnerschaft")
    johann, maria, franz, gerti = (
        person_model.objects.create(vornamen=name) for name in ("Johann", "Maria", "Franz", "Gerti")
    )
    paare = {
        "ehe": partnerschaft_model.objects.create(
            person_a=johann, person_b=maria, art="ehe", beginn="1985", ende="ABT 2001"
        ),
        "lebensgemeinschaft": partnerschaft_model.objects.create(
            person_a=franz, person_b=gerti, art="lebensgemeinschaft", beginn="BET 1990 AND 1992"
        ),
        "unlesbar": partnerschaft_model.objects.create(person_a=johann, person_b=franz, art="ehe", beginn="im Krieg"),
    }
    yield paare
    MigrationExecutor(connection).migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())


def _apps_nach(ziel: list[tuple[str, str]]) -> StateApps:
    executor = MigrationExecutor(connection)
    executor.migrate(ziel)
    return executor.loader.project_state(ziel).apps


def test_migration_turns_a_marriage_into_geheiratet_and_geschieden(paare_vor_8):
    angabe_model = _apps_nach(NACHHER).get_model("stammbaum", "Angabe")

    angaben = set(
        angabe_model.objects.filter(partnerschaft_id=paare_vor_8["ehe"].pk).values_list(
            "art", "datum_art", "datum_1", "genauigkeit"
        )
    )

    assert angaben == {
        ("geheiratet", "genau", datetime.date(1985, 1, 1), "jahr"),
        ("geschieden", "ungefaehr", datetime.date(2001, 1, 1), "jahr"),
    }


def test_migration_keeps_the_start_of_any_other_couple_as_its_own_angabe(paare_vor_8):
    angabe_model = _apps_nach(NACHHER).get_model("stammbaum", "Angabe")

    angabe = angabe_model.objects.get(partnerschaft_id=paare_vor_8["lebensgemeinschaft"].pk)

    assert (angabe.art, angabe.bezeichnung, angabe.datum_2, angabe.sortierdatum) == (
        "eigene",
        "Beginn der Partnerschaft",
        datetime.date(1992, 1, 1),
        datetime.date(1991, 7, 2),
    )


def test_migration_keeps_an_unreadable_date_raw(paare_vor_8):
    partnerschaft_model = _apps_nach(NACHHER).get_model("stammbaum", "Partnerschaft")

    roh = partnerschaft_model.objects.get(pk=paare_vor_8["unlesbar"].pk).gedcom_roh

    assert roh == [{"tag": "MARR", "date": "im Krieg"}]


def test_migration_back_writes_the_dates_into_beginn_and_ende_again(paare_vor_8):
    _apps_nach(NACHHER)
    partnerschaft_model = _apps_nach(VORHER).get_model("stammbaum", "Partnerschaft")

    texte = set(partnerschaft_model.objects.exclude(beginn="", ende="").values_list("beginn", "ende"))

    assert texte == {("1985", "ABT 2001"), ("BET 1990 AND 1992", "")}
