"""
How the backups are spoken of (#33): how long ago the last one was, whether another one is due, and how big
something is. Pure functions: no database, no clock - the caller says what day it is.
"""

import datetime
from dataclasses import dataclass

# From this many days without a backup the sidebar says one is due.
OVERDUE_DAYS = 7


@dataclass(frozen=True, kw_only=True)
class BackupAge:
    # "heute", "gestern", "vor 3 Tagen" or "noch nie", to follow "Zuletzt gesichert: ".
    text: str
    overdue: bool


def backup_age(*, last_backup_on: datetime.date | None, today: datetime.date) -> BackupAge:
    """
    How long ago the last backup was, counted in calendar days, and whether another one is due: after
    "OVERDUE_DAYS" days, and when there has never been one.
    """
    if last_backup_on is None:
        return BackupAge(text="noch nie", overdue=True)

    days = (today - last_backup_on).days
    if days <= 0:
        text = "heute"
    elif days == 1:
        text = "gestern"
    else:
        text = f"vor {days} Tagen"
    return BackupAge(text=text, overdue=days >= OVERDUE_DAYS)


def format_size(*, size: int) -> str:
    """
    A number of bytes the German way, in megabytes below a gigabyte and in gigabytes from there: "12,3 MB",
    "48,0 GB" - and "1,0 GB" rather than "1000,0 MB" for what rounds up to a gigabyte.
    """
    megabytes = round(size / 1_000_000, 1)
    if megabytes < 1000:
        return f"{megabytes:.1f} MB".replace(".", ",")
    return f"{size / 1_000_000_000:.1f} GB".replace(".", ",")
