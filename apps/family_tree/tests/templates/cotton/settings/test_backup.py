from django.urls import reverse

from apps.common.tests.html import parse, render_component
from apps.family_tree.readers.backup import BackupFolder

TAG = '<c-settings.backup :tree_id="tree_id" :backup_folder="backup_folder" />'


def test_backup_posts_the_folder_entered():
    html = render_component(
        tag='<c-settings.backup :backup_folder="backup_folder" />',
        context={"tree_id": 3, "backup_folder": BackupFolder(path="/mnt/sicherung", free="48,2 GB")},
    )

    form = parse(html).find("input", attrs={"name": "backup_dir"}).find_parent("form")
    assert (form["data-on:submit"], form.find("input", attrs={"name": "backup_dir"})["value"]) == (
        f"@post('{reverse('family_tree:backup-dir-view', kwargs={'tree_pk': 3})}', {{contentType: 'form'}})",
        "/mnt/sicherung",
    )


def test_backup_says_how_much_space_is_left():
    html = render_component(
        tag='<c-settings.backup :backup_folder="backup_folder" />',
        context={"tree_id": 3, "backup_folder": BackupFolder(path="/mnt/sicherung", free="48,2 GB")},
    )

    assert parse(html).find(string="Frei: 48,2 GB") is not None


def test_backup_says_when_the_folder_cannot_be_reached():
    html = render_component(
        tag='<c-settings.backup :backup_folder="backup_folder" />',
        context={"tree_id": 3, "backup_folder": BackupFolder(path="/mnt/sicherung", free="")},
    )

    assert "nicht erreichbar" in parse(html).find(id="backup").get_text()


def test_backup_button_makes_a_backup():
    html = render_component(
        tag='<c-settings.backup :backup_folder="backup_folder" />',
        context={"tree_id": 3, "backup_folder": BackupFolder(path="/mnt/sicherung", free="48,2 GB")},
    )

    assert parse(html).find("button", string="Jetzt sichern").find_parent("form")["data-on:submit"] == (
        f"@post('{reverse('family_tree:backup-view', kwargs={'tree_pk': 3})}', {{contentType: 'form'}})"
    )


def test_backup_button_is_disabled_without_a_folder():
    html = render_component(
        tag='<c-settings.backup :backup_folder="backup_folder" />',
        context={"tree_id": 3, "backup_folder": BackupFolder(path="", free="")},
    )

    assert parse(html).find("button", string="Jetzt sichern").has_attr("disabled") is True
