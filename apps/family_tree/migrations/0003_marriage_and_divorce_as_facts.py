"""
Turns the GEDCOM date text that Partnership.start and .end held until #8 into facts on the Partnership - see
docs/patterns/evidence.md. For a marriage they are "marriage" and "divorce"; for any other couple they are
custom facts "Beginn der Partnerschaft" and "Ende der Partnerschaft", because the start of a cohabitation is
not a wedding. A text that is not a date this migration can read is kept in the Partnership's "gedcom_raw"
instead of being lost.

The date reading is frozen in here rather than imported from "domain.dates": a migration has to do the same
thing on every database it ever runs on, whatever that module becomes.
"""

import datetime
import re

from django.db import migrations
from django.db.models import Q

MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
PREFIXES = {"ABT": "about", "EST": "about", "CAL": "about", "BEF": "before", "AFT": "after"}
GEDCOM_PREFIX = {"about": "ABT", "before": "BEF", "after": "AFT"}
SIMPLE_DATE = re.compile(r"^(?:(?:(\d{1,2}) )?([A-Z]{3}) )?(\d{3,4})$")

# (field, tag, kind for a marriage, label of the custom fact for any other couple)
FIELDS = (
    ("start", "MARR", "marriage", "Beginn der Partnerschaft"),
    ("end", "DIV", "divorce", "Ende der Partnerschaft"),
)


def _simple_date(text: str) -> tuple[datetime.date, str]:
    match = SIMPLE_DATE.match(text)
    if match is None:
        raise ValueError(text)
    day, month, year = match.groups()
    if month is not None and month not in MONTHS:
        raise ValueError(text)
    if day is not None:
        return datetime.date(int(year), MONTHS.index(month) + 1, int(day)), "day"
    if month is not None:
        return datetime.date(int(year), MONTHS.index(month) + 1, 1), "month"
    return datetime.date(int(year), 1, 1), "year"


def _read(text: str) -> tuple[str, datetime.date, datetime.date | None, str, datetime.date]:
    """
    (date_kind, date_1, date_2, precision, sort_date), or ValueError.
    """
    parts = text.strip().upper().split()
    if parts and parts[0] == "BET" and "AND" in parts:
        and_at = parts.index("AND")
        date_1, precision = _simple_date(" ".join(parts[1:and_at]))
        date_2, precision_2 = _simple_date(" ".join(parts[and_at + 1 :]))
        if precision_2 != precision or date_2 < date_1:
            raise ValueError(text)
        end = datetime.date(date_2.year, 12, 31) if precision == "year" else date_2
        return "between", date_1, date_2, precision, date_1 + (end - date_1) / 2
    kind = PREFIXES.get(parts[0]) if parts else None
    date_1, precision = _simple_date(" ".join(parts[1:] if kind else parts))
    return kind or "exact", date_1, None, precision, date_1


def _to_gedcom(fact) -> str:
    def simple(date: datetime.date) -> str:
        if fact.precision == "day":
            return f"{date.day} {MONTHS[date.month - 1]} {date.year}"
        if fact.precision == "month":
            return f"{MONTHS[date.month - 1]} {date.year}"
        return str(date.year)

    if fact.date_kind == "between":
        return f"BET {simple(fact.date_1)} AND {simple(fact.date_2)}"
    if fact.date_kind == "exact":
        return simple(fact.date_1)
    return f"{GEDCOM_PREFIX[fact.date_kind]} {simple(fact.date_1)}"


def forwards(apps, schema_editor):
    Partnership = apps.get_model("family_tree", "Partnership")
    Fact = apps.get_model("family_tree", "Fact")
    for partnership in Partnership.objects.exclude(start="", end=""):
        for field, tag, marriage_kind, label in FIELDS:
            text = getattr(partnership, field)
            if not text:
                continue
            try:
                date_kind, date_1, date_2, precision, sort_date = _read(text)
            except ValueError:
                partnership.gedcom_raw = [*partnership.gedcom_raw, {"tag": tag, "date": text}]
                partnership.save(update_fields=["gedcom_raw"])
                continue
            married = partnership.kind == "marriage"
            Fact.objects.create(
                partnership=partnership,
                kind=marriage_kind if married else "custom",
                label="" if married else label,
                date_kind=date_kind,
                date_1=date_1,
                date_2=date_2,
                precision=precision,
                sort_date=sort_date,
            )


def backwards(apps, schema_editor):
    """
    Writes the dates back into "start" and "end", so going back to before #8 keeps them.
    """
    Fact = apps.get_model("family_tree", "Fact")
    for field, _tag, marriage_kind, label in FIELDS:
        for fact in Fact.objects.filter(partnership__isnull=False, date_1__isnull=False).filter(
            Q(kind=marriage_kind) | Q(kind="custom", label=label)
        ):
            setattr(fact.partnership, field, _to_gedcom(fact))
            fact.partnership.save(update_fields=[field])


class Migration(migrations.Migration):
    dependencies = [
        ("family_tree", "0002_facts_sources_citations"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
