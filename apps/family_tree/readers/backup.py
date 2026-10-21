"""
What the screens show about backups (#33): how long ago the last one was, and the folder they go to.
"""

from dataclasses import dataclass
from pathlib import Path
from shutil import disk_usage

from django.utils.timezone import localdate, localtime

from apps.family_tree.domain.backup import BackupAge, backup_age, format_size
from apps.family_tree.models import TreeSettings


@dataclass(frozen=True, kw_only=True)
class BackupFolder:
    # The folder of the settings, empty while none is set.
    path: str
    # The space still free there, "48,3 GB" - empty while there is no folder or it cannot be reached, a disk
    # unplugged perhaps.
    free: str


def last_backup() -> BackupAge:
    """
    How long ago the last backup was, for "Zuletzt gesichert" in the sidebar - in local days, from today.
    """
    last_backup_at = (
        TreeSettings.objects.filter(pk=TreeSettings.ONLY_ROW).values_list("last_backup_at", flat=True).first()
    )
    return backup_age(
        last_backup_on=localtime(last_backup_at).date() if last_backup_at else None,
        today=localdate(),
    )


def backup_folder() -> BackupFolder:
    """
    The folder backups go to and the space left on it, for the settings page.
    """
    path = TreeSettings.objects.filter(pk=TreeSettings.ONLY_ROW).values_list("backup_dir", flat=True).first() or ""
    free = format_size(size=disk_usage(path).free) if path and Path(path).is_dir() else ""
    return BackupFolder(path=path, free=free)
