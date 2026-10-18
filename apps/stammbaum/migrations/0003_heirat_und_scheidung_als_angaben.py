"""
Turns the GEDCOM date text that Partnerschaft.beginn and .ende held until #8 into Angaben "Geheiratet" and
"Geschieden" on the Partnerschaft - see docs/patterns/belege.md. A text that is not a date Zweigerl can read
is kept in the Partnerschaft's "gedcom_roh" instead of being lost.
"""

from django.db import migrations

from apps.stammbaum.domain.datum import aus_gedcom, sortierdatum

ARTEN = (("beginn", "geheiratet", "MARR"), ("ende", "geschieden", "DIV"))


def heirat_und_scheidung_als_angaben(apps, schema_editor):
    Partnerschaft = apps.get_model("stammbaum", "Partnerschaft")
    Angabe = apps.get_model("stammbaum", "Angabe")
    for partnerschaft in Partnerschaft.objects.exclude(beginn="", ende=""):
        for feld, art, tag in ARTEN:
            text = getattr(partnerschaft, feld)
            if not text:
                continue
            try:
                datum = aus_gedcom(text=text)
            except ValueError:
                partnerschaft.gedcom_roh = [*partnerschaft.gedcom_roh, {"tag": tag, "date": text}]
                partnerschaft.save(update_fields=["gedcom_roh"])
                continue
            Angabe.objects.create(
                partnerschaft=partnerschaft,
                art=art,
                datum_art=datum.art,
                datum_1=datum.datum_1,
                datum_2=datum.datum_2,
                genauigkeit=datum.genauigkeit,
                sortierdatum=sortierdatum(datum=datum),
            )


class Migration(migrations.Migration):
    dependencies = [
        ("stammbaum", "0002_angaben_quellen_zitate"),
    ]

    operations = [
        migrations.RunPython(heirat_und_scheidung_als_angaben, migrations.RunPython.noop),
    ]
