"""
Gives what migration 0003 kept in a Partnership's "gedcom_raw" the shape every entry has since #26: a GEDCOM
structure {"tag", "value", "children"}, which the export writes back as it is - see docs/patterns/family.md,
"Raw GEDCOM". 0003 kept a date it could not read as {"tag": "MARR", "date": "im Krieg"}: a MARR with that DATE
below it.
"""

from django.db import migrations

LEGACY_KEYS = {"tag", "date"}


def forwards(apps, schema_editor):
    Partnership = apps.get_model("family_tree", "Partnership")
    for partnership in Partnership.objects.all():
        raw = [
            {"tag": entry["tag"], "children": [{"tag": "DATE", "value": entry["date"]}]}
            if set(entry) == LEGACY_KEYS
            else entry
            for entry in partnership.gedcom_raw
        ]
        if raw != partnership.gedcom_raw:
            Partnership.objects.filter(pk=partnership.pk).update(gedcom_raw=raw)


def backwards(apps, schema_editor):
    """
    Back to the shape 0003 wrote, so that going back to before #26 keeps the dates.
    """
    Partnership = apps.get_model("family_tree", "Partnership")
    for partnership in Partnership.objects.all():
        raw = [
            {"tag": entry["tag"], "date": entry["children"][0]["value"]} if _is_date_only(entry=entry) else entry
            for entry in partnership.gedcom_raw
        ]
        if raw != partnership.gedcom_raw:
            Partnership.objects.filter(pk=partnership.pk).update(gedcom_raw=raw)


def _is_date_only(*, entry: dict) -> bool:
    children = entry.get("children", [])
    return (
        set(entry) == {"tag", "children"}
        and entry["tag"] in ("MARR", "DIV")
        and len(children) == 1
        and set(children[0]) == {"tag", "value"}
        and children[0]["tag"] == "DATE"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("family_tree", "0006_photo"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
