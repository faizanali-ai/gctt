from django.db import migrations

OWNER_EMAIL = "ceo@gctekton.com"


def set_roles(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    # The existing platform account becomes the owner; other staff keep staff role.
    User.objects.filter(email=OWNER_EMAIL).update(
        role="owner", is_staff=True, is_superuser=True
    )
    User.objects.filter(is_staff=True).exclude(email=OWNER_EMAIL).update(role="staff")


def unset_roles(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.update(role="staff")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_user_role"),
    ]

    operations = [
        migrations.RunPython(set_roles, unset_roles),
    ]
