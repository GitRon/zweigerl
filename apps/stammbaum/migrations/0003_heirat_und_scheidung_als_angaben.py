"""
Turns the GEDCOM date text that Partnerschaft.beginn and .ende held until #8 into Angaben on the
Partnerschaft - see docs/patterns/belege.md. For an Ehe they are "Geheiratet" and "Geschieden"; for any other
couple they are own Angaben "Beginn der Partnerschaft" and "Ende der Partnerschaft", because the start of a
Lebensgemeinschaft is not a wedding. A text that is not a date this migration can read is kept in the
Partnerschaft's "gedcom_roh" instead of being lost.

The date reading is frozen in here rather than imported from "domain.datum": a migration has to do the same
thing on every database it ever runs on, whatever that module becomes.
"""

import datetime
import re

from django.db import migrations
from django.db.models import Q

MONATE = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
PRAEFIXE = {"ABT": "ungefaehr", "EST": "ungefaehr", "CAL": "ungefaehr", "BEF": "vor", "AFT": "nach"}
GEDCOM_PRAEFIX = {"ungefaehr": "ABT", "vor": "BEF", "nach": "AFT"}
EINFACHES_DATUM = re.compile(r"^(?:(?:(\d{1,2}) )?([A-Z]{3}) )?(\d{3,4})$")

# (field, tag, Art for an Ehe, label of the own Angabe for any other couple)
FELDER = (
    ("beginn", "MARR", "geheiratet", "Beginn der Partnerschaft"),
    ("ende", "DIV", "geschieden", "Ende der Partnerschaft"),
)


def _einfaches_datum(text: str) -> tuple[datetime.date, str]:
    treffer = EINFACHES_DATUM.match(text)
    if treffer is None:
        raise ValueError(text)
    tag, monat, jahr = treffer.groups()
    if monat is not None and monat not in MONATE:
        raise ValueError(text)
    if tag is not None:
        return datetime.date(int(jahr), MONATE.index(monat) + 1, int(tag)), "tag"
    if monat is not None:
        return datetime.date(int(jahr), MONATE.index(monat) + 1, 1), "monat"
    return datetime.date(int(jahr), 1, 1), "jahr"


def _lies(text: str) -> tuple[str, datetime.date, datetime.date | None, str, datetime.date]:
    """
    (datum_art, datum_1, datum_2, genauigkeit, sortierdatum), or ValueError.
    """
    teile = text.strip().upper().split()
    if teile and teile[0] == "BET" and "AND" in teile:
        und = teile.index("AND")
        datum_1, genauigkeit = _einfaches_datum(" ".join(teile[1:und]))
        datum_2, genauigkeit_2 = _einfaches_datum(" ".join(teile[und + 1 :]))
        if genauigkeit_2 != genauigkeit or datum_2 < datum_1:
            raise ValueError(text)
        ende = datetime.date(datum_2.year, 12, 31) if genauigkeit == "jahr" else datum_2
        return "zwischen", datum_1, datum_2, genauigkeit, datum_1 + (ende - datum_1) / 2
    art = PRAEFIXE.get(teile[0]) if teile else None
    datum_1, genauigkeit = _einfaches_datum(" ".join(teile[1:] if art else teile))
    return art or "genau", datum_1, None, genauigkeit, datum_1


def _als_gedcom(angabe) -> str:
    def einfach(datum: datetime.date) -> str:
        if angabe.genauigkeit == "tag":
            return f"{datum.day} {MONATE[datum.month - 1]} {datum.year}"
        if angabe.genauigkeit == "monat":
            return f"{MONATE[datum.month - 1]} {datum.year}"
        return str(datum.year)

    if angabe.datum_art == "zwischen":
        return f"BET {einfach(angabe.datum_1)} AND {einfach(angabe.datum_2)}"
    if angabe.datum_art == "genau":
        return einfach(angabe.datum_1)
    return f"{GEDCOM_PRAEFIX[angabe.datum_art]} {einfach(angabe.datum_1)}"


def vorwaerts(apps, schema_editor):
    Partnerschaft = apps.get_model("stammbaum", "Partnerschaft")
    Angabe = apps.get_model("stammbaum", "Angabe")
    for partnerschaft in Partnerschaft.objects.exclude(beginn="", ende=""):
        for feld, tag, ehe_art, bezeichnung in FELDER:
            text = getattr(partnerschaft, feld)
            if not text:
                continue
            try:
                datum_art, datum_1, datum_2, genauigkeit, sortierdatum = _lies(text)
            except ValueError:
                partnerschaft.gedcom_roh = [*partnerschaft.gedcom_roh, {"tag": tag, "date": text}]
                partnerschaft.save(update_fields=["gedcom_roh"])
                continue
            ehe = partnerschaft.art == "ehe"
            Angabe.objects.create(
                partnerschaft=partnerschaft,
                art=ehe_art if ehe else "eigene",
                bezeichnung="" if ehe else bezeichnung,
                datum_art=datum_art,
                datum_1=datum_1,
                datum_2=datum_2,
                genauigkeit=genauigkeit,
                sortierdatum=sortierdatum,
            )


def rueckwaerts(apps, schema_editor):
    """
    Writes the dates back into "beginn" and "ende", so going back to before #8 keeps them.
    """
    Angabe = apps.get_model("stammbaum", "Angabe")
    for feld, _tag, ehe_art, bezeichnung in FELDER:
        for angabe in Angabe.objects.filter(partnerschaft__isnull=False, datum_1__isnull=False).filter(
            Q(art=ehe_art) | Q(art="eigene", bezeichnung=bezeichnung)
        ):
            setattr(angabe.partnerschaft, feld, _als_gedcom(angabe))
            angabe.partnerschaft.save(update_fields=[feld])


class Migration(migrations.Migration):
    dependencies = [
        ("stammbaum", "0002_angaben_quellen_zitate"),
    ]

    operations = [
        migrations.RunPython(vorwaerts, rueckwaerts),
    ]
