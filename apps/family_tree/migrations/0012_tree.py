"""
Several trees in one installation (#34). Everything already entered goes into one tree named "Stammbaum", which
takes over the home person of the settings; an installation with nothing in it gets no tree and asks for its first
one. The settings that are left - where backups go and when the last one was - belong to the installation, so the
model is renamed to say so.
"""

import ambient_toolbox.mixins.validation
import django.db.models.deletion
from django.db import migrations, models

ROOT_MODELS = ("Person", "Source", "Photo", "GedcomImport")
MIGRATED_TREE_NAME = "Stammbaum"


def forwards(apps, schema_editor) -> None:
    tree_settings = apps.get_model("family_tree", "TreeSettings").objects.filter(pk=1).first()
    home_person_id = tree_settings.home_person_id if tree_settings else None
    roots = [apps.get_model("family_tree", name) for name in ROOT_MODELS]
    if home_person_id is None and not any(model.objects.exists() for model in roots):
        return

    tree = apps.get_model("family_tree", "Tree").objects.create(
        name=MIGRATED_TREE_NAME, home_person_id=home_person_id
    )
    for model in roots:
        model.objects.update(tree=tree)


def backwards(apps, schema_editor) -> None:
    tree = apps.get_model("family_tree", "Tree").objects.order_by("pk").first()
    if tree is not None and tree.home_person_id is not None:
        apps.get_model("family_tree", "TreeSettings").objects.update_or_create(
            pk=1, defaults={"home_person_id": tree.home_person_id}
        )


def _tree_field(*, related_name: str, null: bool) -> models.ForeignKey:
    return models.ForeignKey(
        null=null,
        on_delete=django.db.models.deletion.PROTECT,
        related_name=related_name,
        to="family_tree.tree",
        verbose_name="Stammbaum",
    )


RELATED_NAMES = {"person": "people", "source": "sources", "photo": "photos", "gedcomimport": "imports"}


class Migration(migrations.Migration):

    dependencies = [
        ("family_tree", "0011_note"),
    ]

    operations = [
        migrations.CreateModel(
            name="Tree",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, verbose_name="Name")),
                (
                    "home_person",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="family_tree.person",
                        verbose_name="Ausgangsperson",
                    ),
                ),
            ],
            options={
                "verbose_name": "Stammbaum",
                "verbose_name_plural": "Stammbäume",
                "ordering": ("name", "pk"),
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("name", ""), _negated=True),
                        name="tree_has_name",
                        violation_error_message="Ein Stammbaum braucht einen Namen, etwa „Familie Huber“.",
                    ),
                    models.UniqueConstraint(
                        fields=("name",),
                        name="tree_name_once",
                        violation_error_message="Einen Stammbaum mit diesem Namen gibt es schon.",
                    ),
                ],
            },
            bases=(ambient_toolbox.mixins.validation.ValidateConstraintsOnSaveMixin, models.Model),
        ),
        *(
            migrations.AddField(model_name=model, name="tree", field=_tree_field(related_name=related, null=True))
            for model, related in RELATED_NAMES.items()
        ),
        migrations.RunPython(forwards, backwards),
        *(
            migrations.AlterField(model_name=model, name="tree", field=_tree_field(related_name=related, null=False))
            for model, related in RELATED_NAMES.items()
        ),
        migrations.RemoveField(model_name="treesettings", name="home_person"),
        migrations.RemoveConstraint(model_name="treesettings", name="treesettings_single_row"),
        migrations.RenameModel(old_name="TreeSettings", new_name="InstallationSettings"),
        migrations.AddConstraint(
            model_name="installationsettings",
            constraint=models.CheckConstraint(
                condition=models.Q(("id", 1)),
                name="installationsettings_single_row",
                violation_error_message="Es gibt nur eine Zeile Einstellungen.",
            ),
        ),
    ]
