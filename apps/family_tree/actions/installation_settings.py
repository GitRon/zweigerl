from pathlib import Path

from apps.family_tree.actions.backup import check_backup_dir
from apps.family_tree.models import InstallationSettings


def set_backup_dir(*, backup_dir: str) -> InstallationSettings:
    """
    Keeps the folder backups go to (#33), as the absolute path "check_backup_dir" makes of it - and refuses it
    with "BackupRefusedError" wherever a backup would be refused too. An empty one clears the setting.
    """
    backup_dir = backup_dir.strip()
    if backup_dir:
        backup_dir = str(check_backup_dir(path=Path(backup_dir)))
    installation_settings, _ = InstallationSettings.objects.update_or_create(
        pk=InstallationSettings.ONLY_ROW, defaults={"backup_dir": backup_dir}
    )
    return installation_settings
