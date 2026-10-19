from pathlib import Path

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.family_tree.actions.backup import BackupRefusedError, create_backup
from apps.family_tree.readers.gedcom import gedcom_export


class Command(BaseCommand):
    help = "Sichert Datenbank, GEDCOM und Medien in einen Ordner mit Zeitstempel (#27)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--target", type=Path, help="Ein anderer Ordner als der eingestellte, etwa auf einer externen Platte."
        )

    def handle(self, *args, **options) -> None:
        try:
            backup = create_backup(gedcom=gedcom_export(), target=options["target"])
        except BackupRefusedError as error:
            raise CommandError(str(error)) from error

        megabytes = f"{backup.size / 1_000_000:.1f}".replace(".", ",")
        self.stdout.write(f"Gesichert in {backup.path}")
        self.stdout.write(f"{megabytes} MB, Personen: {backup.people}, Dateien: {backup.files}")
        for folder in backup.incomplete:
            self.stdout.write(f"Unvollständig liegen geblieben: {folder}")
