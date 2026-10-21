from pathlib import Path

from apps.family_tree.actions.backup import check_backup_dir
from apps.family_tree.models import Person, TreeSettings


def choose_home_person(*, person_id: int) -> TreeSettings:
    """
    Makes the person the home person, whom the tree is laid out around and relationships are named from
    (#20). Raises "Person.DoesNotExist" for somebody who is not in the tree, deleted in the meantime perhaps.
    """
    tree_settings, _ = TreeSettings.objects.update_or_create(
        pk=TreeSettings.ONLY_ROW, defaults={"home_person": Person.objects.get(pk=person_id)}
    )
    return tree_settings


def set_backup_dir(*, backup_dir: str) -> TreeSettings:
    """
    Keeps the folder backups go to (#33), as the absolute path "check_backup_dir" makes of it - and refuses it
    with "BackupRefusedError" wherever a backup would be refused too. An empty one clears the setting.
    """
    backup_dir = backup_dir.strip()
    if backup_dir:
        backup_dir = str(check_backup_dir(path=Path(backup_dir)))
    tree_settings, _ = TreeSettings.objects.update_or_create(
        pk=TreeSettings.ONLY_ROW, defaults={"backup_dir": backup_dir}
    )
    return tree_settings
