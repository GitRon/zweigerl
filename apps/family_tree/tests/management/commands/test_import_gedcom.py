import io

import pytest
from django.core.management import CommandError, call_command


@pytest.mark.django_db
def test_import_gedcom_says_what_it_imported_under_which_name(tmp_path):
    file = tmp_path / "huber.ged"
    file.write_bytes(b"0 HEAD\n0 @I1@ INDI\n0 @I2@ INDI\n0 @F1@ FAM\n1 HUSB @I1@\n1 WIFE @I2@\n1 MARR\n2 DATE 1989\n")
    output = io.StringIO()

    call_command("import_gedcom", file, name="PAF Huber", stdout=output)

    assert output.getvalue().splitlines() == [
        "Importiert als „PAF Huber“",
        "Personen: 2, Familien: 1, Angaben: 1",
        "Quellen: 0, Zitate: 0, Notizen: 0",
    ]


@pytest.mark.django_db
def test_import_gedcom_says_why_it_refused(tmp_path):
    file = tmp_path / "huber.ged"
    file.write_bytes(b"0 HEAD\n0 @I1@ INDI\n0 TRLR\n")

    with pytest.raises(CommandError, match="Ein Import braucht einen Namen"):
        call_command("import_gedcom", file, name="  ")


def test_import_gedcom_says_when_the_file_cannot_be_opened(tmp_path):
    with pytest.raises(CommandError, match="Die Datei lässt sich nicht öffnen"):
        call_command("import_gedcom", tmp_path / "nirgends.ged", name="PAF Huber")
