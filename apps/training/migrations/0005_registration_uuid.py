import uuid

from django.db import migrations, models


def populate_uuids(apps, schema_editor):
    Registration = apps.get_model("training", "Registration")
    for registration in Registration.objects.filter(uuid__isnull=True).iterator():
        registration.uuid = uuid.uuid4()
        registration.save(update_fields=["uuid"])


class Migration(migrations.Migration):
    dependencies = [
        ("training", "0004_pendingregistration"),
    ]

    operations = [
        migrations.AddField(
            model_name="registration",
            name="uuid",
            field=models.UUIDField(db_index=True, null=True, blank=True),
        ),
        migrations.RunPython(populate_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="registration",
            name="uuid",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, unique=True
            ),
        ),
    ]
