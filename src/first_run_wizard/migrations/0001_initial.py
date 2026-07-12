from django.db import migrations, models


def create_singleton_row(apps, schema_editor):
    State = apps.get_model("first_run_wizard", "FirstRunWizardState")
    State.objects.get_or_create(pk=1)


def delete_singleton_row(apps, schema_editor):
    State = apps.get_model("first_run_wizard", "FirstRunWizardState")
    State.objects.filter(pk=1).delete()


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="FirstRunWizardState",
            fields=[
                (
                    "id",
                    models.PositiveSmallIntegerField(
                        default=1, primary_key=True, serialize=False
                    ),
                ),
                ("admin_created_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "first-run wizard state",
            },
        ),
        migrations.RunPython(create_singleton_row, delete_singleton_row),
    ]
