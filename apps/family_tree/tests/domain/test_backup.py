import datetime

import pytest

from apps.family_tree.domain.backup import BackupAge, backup_age, format_size

TODAY = datetime.date(2026, 10, 21)


def test_backup_age_without_a_backup_is_due():
    assert backup_age(last_backup_on=None, today=TODAY) == BackupAge(text="noch nie", overdue=True)


def test_backup_age_of_today():
    assert backup_age(last_backup_on=TODAY, today=TODAY) == BackupAge(text="heute", overdue=False)


def test_backup_age_of_a_backup_dated_after_today_is_today():
    assert backup_age(last_backup_on=datetime.date(2026, 10, 22), today=TODAY) == BackupAge(
        text="heute", overdue=False
    )


def test_backup_age_of_yesterday():
    assert backup_age(last_backup_on=datetime.date(2026, 10, 20), today=TODAY) == BackupAge(
        text="gestern", overdue=False
    )


def test_backup_age_counts_the_days():
    assert backup_age(last_backup_on=datetime.date(2026, 10, 15), today=TODAY) == BackupAge(
        text="vor 6 Tagen", overdue=False
    )


def test_backup_age_is_due_after_a_week():
    assert backup_age(last_backup_on=datetime.date(2026, 10, 14), today=TODAY) == BackupAge(
        text="vor 7 Tagen", overdue=True
    )


@pytest.mark.parametrize(
    ("size", "text"),
    [(12_345_678, "12,3 MB"), (999_999_999, "1,0 GB"), (48_250_000_000, "48,2 GB")],
)
def test_format_size(size, text):
    assert format_size(size=size) == text
