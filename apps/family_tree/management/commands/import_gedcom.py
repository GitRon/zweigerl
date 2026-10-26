from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from apps.family_tree.actions.gedcom_import import ImportRefusedError, import_gedcom
from apps.family_tree.actions.trees import create_tree
from apps.family_tree.readers.trees import tree_id_by_name


class Command(BaseCommand):
    help = "Liest eine GEDCOM-Datei in einen leeren Stammbaum ein, etwa einen PAF-Export (#22, #34)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("file", type=Path, help="Die GEDCOM-Datei.")
        parser.add_argument(
            "--name", required=True, help="Unter welchem Namen der Import als Herkunft steht, etwa „PAF Ronny“."
        )
        parser.add_argument(
            "--tree",
            required=True,
            help="In welchen Stammbaum, etwa „Familie Huber“. Gibt es ihn noch nicht, wird er angelegt.",
        )

    def handle(self, *args, **options) -> None:
        tree_name = options["tree"].strip()
        tree_id = tree_id_by_name(name=tree_name)
        new_tree = tree_id is None
        try:
            # One transaction, so a refused import leaves no empty tree behind either.
            with transaction.atomic(), options["file"].open("rb") as file:
                if new_tree:
                    tree_id = create_tree(name=tree_name).pk
                result = import_gedcom(tree_id=tree_id, file=file, name=options["name"])
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from error
        except OSError as error:
            raise CommandError(f"Die Datei lässt sich nicht öffnen: {error}") from error
        except ImportRefusedError as error:
            raise CommandError(str(error)) from error

        if new_tree:
            self.stdout.write(f"Stammbaum „{tree_name}“ angelegt")
        self.stdout.write(f"Importiert als „{result.gedcom_import.name}“ in „{tree_name}“")
        self.stdout.write(f"Personen: {result.people}, Familien: {result.families}, Angaben: {result.facts}")
        self.stdout.write(f"Quellen: {result.sources}, Zitate: {result.citations}, Notizen: {result.notes}")
