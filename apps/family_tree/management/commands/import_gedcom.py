from pathlib import Path

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.family_tree.actions.gedcom_import import ImportRefusedError, import_gedcom


class Command(BaseCommand):
    help = "Liest eine GEDCOM-Datei in den Stammbaum ein, etwa einen PAF-Export (#22), neben die Personen, die schon da sind (#85)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("file", type=Path, help="Die GEDCOM-Datei.")
        parser.add_argument(
            "--name", required=True, help="Unter welchem Namen der Import als Herkunft steht, etwa „PAF Ronny“."
        )

    def handle(self, *args, **options) -> None:
        try:
            with options["file"].open("rb") as file:
                result = import_gedcom(file=file, name=options["name"])
        except OSError as error:
            raise CommandError(f"Die Datei lässt sich nicht öffnen: {error}") from error
        except ImportRefusedError as error:
            raise CommandError(str(error)) from error

        self.stdout.write(f"Importiert als „{result.gedcom_import.name}“")
        self.stdout.write(f"Personen: {result.people}, Familien: {result.families}, Angaben: {result.facts}")
        self.stdout.write(f"Quellen: {result.sources}, Zitate: {result.citations}, Notizen: {result.notes}")
