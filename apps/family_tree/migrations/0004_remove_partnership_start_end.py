from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("family_tree", "0003_marriage_and_divorce_as_facts"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="partnership",
            name="start",
        ),
        migrations.RemoveField(
            model_name="partnership",
            name="end",
        ),
    ]
