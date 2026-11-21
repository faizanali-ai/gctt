from django.db import migrations


class Migration(migrations.Migration):
    """Historical data migration intentionally left as a no-op.

    This migration used to create a personal superuser from hardcoded emails
    and an environment password (or a random one). Fresh databases must not
    gain an unknown privileged account. Existing databases already recorded
    this migration as applied, so this no-op does not re-run there.
    """

    dependencies = [
        ("accounts", "0007_role_backfill"),
    ]

    operations = []
