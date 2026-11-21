from django.db import migrations


class Migration(migrations.Migration):
    """Historical data migration intentionally left as a no-op.

    It used to rename/seeded a personal owner, reset that user's password,
    and delete a ``ceo@gctekton.com`` account. Deleting accounts from a
    migration is unsafe and made rollback impossible. Existing databases have
    already applied it; fresh databases must not repeat it.
    """

    dependencies = [
        ("accounts", "0008_owner_setup"),
    ]

    operations = []
