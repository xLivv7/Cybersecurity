"""Install the single initial policy using the historical model."""

from django.db import migrations


def create_initial_settings(apps, schema_editor):
    settings = apps.get_model("security", "SecuritySettings")
    settings.objects.using(schema_editor.connection.alias).create(
        id=1,
        levenshtein_enabled=True,
        password_max_age_days=0,
        idle_timeout_minutes=15,
    )


def remove_initial_settings(apps, schema_editor):
    settings = apps.get_model("security", "SecuritySettings")
    settings.objects.using(schema_editor.connection.alias).filter(pk=1).delete()


class Migration(migrations.Migration):
    dependencies = [("security", "0001_initial")]

    operations = [
        migrations.RunPython(create_initial_settings, remove_initial_settings),
    ]
