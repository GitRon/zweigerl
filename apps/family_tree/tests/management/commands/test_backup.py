import datetime
import io
from unittest import mock

import pytest
from django.core.management import CommandError, call_command

from apps.family_tree.tests.factories.person import PersonFactory

MOMENT = datetime.datetime(2026, 10, 19, 14, 30, 12, tzinfo=datetime.UTC)


@pytest.mark.django_db(transaction=True)
@mock.patch("apps.family_tree.actions.backup.localtime", return_value=MOMENT)
def test_backup_says_where_it_went_and_what_it_holds(_localtime, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    target = tmp_path / "backups"
    target.mkdir()
    PersonFactory()
    output = io.StringIO()

    call_command("backup", target=target, stdout=output)

    first, second = output.getvalue().splitlines()
    assert first == f"Gesichert in {target.resolve() / '2026-10-19_143012'}"
    assert second.endswith(" MB, Personen: 1, Dateien: 0")


@pytest.mark.django_db(transaction=True)
def test_backup_names_what_an_earlier_run_left_incomplete(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    leftover = tmp_path / "2026-10-18_090000.incomplete"
    leftover.mkdir()
    output = io.StringIO()

    call_command("backup", target=tmp_path, stdout=output)

    assert output.getvalue().splitlines()[-1] == f"Unvollständig liegen geblieben: {leftover.resolve()}"


@pytest.mark.django_db
def test_backup_turns_a_refusal_into_a_command_error(tmp_path):
    with pytest.raises(CommandError, match="gibt es nicht"):
        call_command("backup", target=tmp_path / "unplugged-disk")
