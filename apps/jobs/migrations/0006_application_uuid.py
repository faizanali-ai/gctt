import uuid

from django.db import migrations, models


def populate_uuids(apps, schema_editor):
    Application = apps.get_model("jobs", "Application")
    for application in Application.objects.filter(uuid__isnull=True).iterator():
        application.uuid = uuid.uuid4()
        application.save(update_fields=["uuid"])


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0005_pendingapplication"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="uuid",
            field=models.UUIDField(db_index=True, null=True, blank=True),
        ),
        migrations.RunPython(populate_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="application",
            name="uuid",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, unique=True
            ),
        ),
    ]
