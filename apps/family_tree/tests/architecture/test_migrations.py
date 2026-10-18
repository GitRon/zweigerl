import io

import pytest
from django.core.management import call_command


# "makemigrations" checks the migration history against the database before it compares, hence the mark.
@pytest.mark.django_db
def test_every_model_change_has_its_migration():
    # A constraint that lives in the model but has no migration passes every test through the mixin and never
    # reaches the database. The apps are named because "makemigrations" on its own skips an app that has no
    # "migrations/" yet, which is exactly the state the first model arrives in.
    output = io.StringIO()

    call_command("makemigrations", "family_tree", "common", dry_run=True, stdout=output)

    assert "No changes detected" in output.getvalue(), output.getvalue()
