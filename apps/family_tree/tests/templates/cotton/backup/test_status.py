from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.domain.backup import BackupAge


def test_status_says_how_long_ago_the_last_backup_was():
    html = render_component(
        tag='<c-backup.status :last_backup="last_backup" />',
        context={"last_backup": BackupAge(text="vor 2 Tagen", overdue=False)},
    )

    assert parse(html).get_text(" ", strip=True) == "Zuletzt gesichert: vor 2 Tagen"


def test_status_of_a_backup_that_is_due_leads_to_the_button():
    html = render_component(
        tag='<c-backup.status :last_backup="last_backup" />',
        context={"last_backup": BackupAge(text="vor 9 Tagen", overdue=True)},
    )

    link = parse(html).find("a")
    assert (link.get_text(strip=True), link["href"]) == (
        "Sicherung fällig",
        f"{reverse('family_tree:tree-settings-view')}#backup",
    )
