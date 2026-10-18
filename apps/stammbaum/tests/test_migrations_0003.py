"""
The data migration that turns Partnerschaft.beginn and .ende into Angaben (#8). Migrations are not measured
by the coverage gate, but this one rewrites data the family entered, so it is played once on a real schema.
"""

import datetime

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

VORHER = [("stammbaum", "0002_angaben_quellen_zitate")]
NACHHER = [("stammbaum", "0004_remove_partnerschaft_beginn_ende")]


@pytest.mark.django_db(transaction=True)
def test_migration_turns_beginn_and_ende_into_angaben():
    executor = MigrationExecutor(connection)
    executor.migrate(VORHER)
    alte_apps = executor.loader.project_state(VORHER).apps
    Person = alte_apps.get_model("stammbaum", "Person")
    Partnerschaft = alte_apps.get_model("stammbaum", "Partnerschaft")
    johann = Person.objects.create(vornamen="Johann", familienname="Huber")
    maria = Person.objects.create(vornamen="Maria", familienname="Huber")
    franz = Person.objects.create(vornamen="Franz", familienname="Huber")
    Partnerschaft.objects.create(person_a=johann, person_b=maria, beginn="1985", ende="ABT 2001")
    unlesbar = Partnerschaft.objects.create(person_a=johann, person_b=franz, beginn="im Krieg")

    executor = MigrationExecutor(connection)
    executor.migrate(NACHHER)
    neue_apps = executor.loader.project_state(NACHHER).apps
    Angabe = neue_apps.get_model("stammbaum", "Angabe")
    angaben = set(Angabe.objects.values_list("art", "datum_art", "datum_1", "genauigkeit"))
    roh = neue_apps.get_model("stammbaum", "Partnerschaft").objects.get(pk=unlesbar.pk).gedcom_roh

    assert (angaben, roh) == (
        {
            ("geheiratet", "genau", datetime.date(1985, 1, 1), "jahr"),
            ("geschieden", "ungefaehr", datetime.date(2001, 1, 1), "jahr"),
        },
        [{"tag": "MARR", "date": "im Krieg"}],
    )
