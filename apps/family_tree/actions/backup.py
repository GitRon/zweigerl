"""
The backup of everything a person entered (#27): one timestamped folder with the database, an SQL dump, the
GEDCOM export of every tree and the media - see docs/patterns/data-storage.md, "Backups".
"""

import shutil
import sqlite3
from dataclasses import dataclass
from os import W_OK, access
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.utils.timezone import localtime

from apps.family_tree.models import InstallationSettings, Person

# A folder still being written. It never counts as a backup, and a run that died leaves it behind under this name.
INCOMPLETE_SUFFIX = ".incomplete"
STAMP_FORMAT = "%Y-%m-%d_%H%M%S"


class BackupRefusedError(Exception):
    """
    A backup that cannot be written where it was asked to go, with a German message saying why.
    """


@dataclass(frozen=True, kw_only=True)
class Backup:
    path: Path
    size: int
    people: int
    files: int
    # Folders an earlier run left half-written, for the person to look at - a backup deletes nothing.
    incomplete: list[Path]


def create_backup(*, gedcoms: dict[str, str], target: Path | None = None) -> Backup:
    """
    Writes a backup of every tree into a new folder named after the moment, in "target" or else in the backup
    folder of the settings: "zweigerl.sqlite3" through VACUUM INTO, which is consistent while the app keeps writing,
    the same state as "zweigerl.sql", the GEDCOM export of each tree in "gedcom/" and the media directory as
    "media/". The folder is written under a ".incomplete" name and renamed once everything is in it, and only then
    is the moment stored as "InstallationSettings.last_backup_at".

    "gedcoms" are the exports of "readers.gedcom.gedcom_exports" by file name, which the caller passes in: an action
    does not call a reader. Must run outside a transaction, since SQLite refuses VACUUM inside one.
    """
    backup_dir = _backup_dir(target=target)
    incomplete = sorted(path for path in backup_dir.glob(f"*{INCOMPLETE_SUFFIX}") if path.is_dir())
    moment = localtime()
    stamp = moment.strftime(STAMP_FORMAT)
    final = backup_dir / stamp
    if final.exists():
        raise BackupRefusedError(
            f"In {backup_dir} gibt es schon eine Sicherung {stamp}. Versuch es gleich noch einmal."
        )

    folder = backup_dir / f"{stamp}{INCOMPLETE_SUFFIX}"
    folder.mkdir()
    database = folder / "zweigerl.sqlite3"
    with connection.cursor() as cursor:
        cursor.execute("VACUUM INTO %s", [str(database)])
    _dump(database=database, dump=folder / "zweigerl.sql")
    gedcom_folder = folder / "gedcom"
    gedcom_folder.mkdir()
    for file_name, gedcom in gedcoms.items():
        # As given: Windows would otherwise write every line ending as CRLF.
        (gedcom_folder / file_name).write_text(gedcom, encoding="utf-8", newline="")
    media = folder / "media"
    if Path(settings.MEDIA_ROOT).is_dir():
        shutil.copytree(settings.MEDIA_ROOT, media)
    else:
        media.mkdir()
    folder.rename(final)
    InstallationSettings.objects.update_or_create(pk=InstallationSettings.ONLY_ROW, defaults={"last_backup_at": moment})

    files = [path for path in final.rglob("*") if path.is_file()]
    return Backup(
        path=final,
        size=sum(path.stat().st_size for path in files),
        people=Person.objects.count(),
        files=sum(1 for path in files if path.is_relative_to(final / "media")),
        incomplete=incomplete,
    )


def check_backup_dir(*, path: Path) -> Path:
    """
    "path" made absolute, refused unless it exists, can be written and lies outside both the data directory and
    the repository - for a backup, and for the settings before they keep it as the backup folder. A missing
    folder is not created: an external disk that is not plugged in must not turn into an empty folder where it
    would be.
    """
    backup_dir = path.expanduser().resolve()
    if not backup_dir.is_dir():
        raise BackupRefusedError(
            f"Den Sicherungsordner {backup_dir} gibt es nicht. Leg ihn an oder steck die Platte an."
        )
    if backup_dir.is_relative_to(Path(settings.DATA_DIR).resolve()):
        raise BackupRefusedError(
            f"{backup_dir} liegt im Datenordner. Eine Sicherung dort ginge mit dem Datenordner verloren."
        )
    if backup_dir.is_relative_to(Path(settings.BASE_DIR).resolve()):
        raise BackupRefusedError(f"{backup_dir} liegt im Repository. Echte Familiendaten gehören nie dorthin.")
    if not access(backup_dir, W_OK):
        raise BackupRefusedError(f"In den Sicherungsordner {backup_dir} darf Zweigerl nicht schreiben.")
    return backup_dir


def _backup_dir(*, target: Path | None) -> Path:
    """
    The folder the backup goes to: "target", else the one of the settings, checked by "check_backup_dir".
    """
    if target is None:
        configured = (
            InstallationSettings.objects.filter(pk=InstallationSettings.ONLY_ROW)
            .values_list("backup_dir", flat=True)
            .first()
        )
        if not configured:
            raise BackupRefusedError(
                "Es ist noch kein Sicherungsordner eingestellt. Trag einen in den Einstellungen ein oder nenn einen "
                "mit --target."
            )
        target = Path(configured)
    return check_backup_dir(path=target)


def _dump(*, database: Path, dump: Path) -> None:
    """
    The copy as SQL text, readable without SQLite and without Zweigerl.
    """
    copy = sqlite3.connect(database)
    try:
        with dump.open("w", encoding="utf-8") as text:
            for line in copy.iterdump():
                text.write(f"{line}\n")
    finally:
        copy.close()
