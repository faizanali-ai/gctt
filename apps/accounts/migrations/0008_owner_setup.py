import os
import secrets

from django.contrib.auth.hashers import make_password
from django.db import migrations

OWNER_EMAIL = os.environ.get("INITIAL_OWNER_EMAIL", "mohdfaizanali30@gmail.com")
OWNER_PASS = os.environ.get("INITIAL_OWNER_PASSWORD") or secrets.token_urlsafe(16)


def setup_owner(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Group = apps.get_model("auth", "Group")

    # Demote old demo owner to superadmin so mohdfaizanali30@gmail.com is the sole primary Owner
    User.objects.filter(email="ceo@gctekton.com").update(role="superadmin")

    user, created = User.objects.get_or_create(
        email=OWNER_EMAIL,
        defaults={
            "first_name": "Faizan",
            "last_name": "Ali",
            "role": "owner",
            "is_staff": True,
            "is_superuser": True,
            "email_verified": True,
            "is_active": True,
            "password": make_password(OWNER_PASS),
        },
    )
    if not created:
        user.role = "owner"
        user.is_staff = True
        user.is_superuser = True
        user.email_verified = True
        user.is_active = True
        user.password = make_password(OWNER_PASS)
        user.save()

    admin_group = Group.objects.filter(name="Admin").first()
    if admin_group:
        user.groups.add(admin_group)


def revert_owner(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(email=OWNER_EMAIL).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_role_backfill"),
    ]

    operations = [
        migrations.RunPython(setup_owner, revert_owner),
    ]
