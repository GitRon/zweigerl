from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("stammbaum", "0003_heirat_und_scheidung_als_angaben"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="partnerschaft",
            name="beginn",
        ),
        migrations.RemoveField(
            model_name="partnerschaft",
            name="ende",
        ),
    ]
