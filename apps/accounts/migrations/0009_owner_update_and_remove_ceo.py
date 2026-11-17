import os
import secrets

from django.contrib.auth.hashers import make_password
from django.db import migrations

OLD_OWNER_EMAIL = "mohdfaizanali30@gmail.com"
NEW_OWNER_EMAIL = os.environ.get("INITIAL_OWNER_EMAIL", "mohdfaizanali038@gmail.com")
OWNER_PASS = os.environ.get("INITIAL_OWNER_PASSWORD") or secrets.token_urlsafe(16)
CEO_EMAIL = "ceo@gctekton.com"


def update_owner_and_purge_ceo(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Group = apps.get_model("auth", "Group")

    # 1. Purge the old ceo account so the owner can add the real CEO themselves
    User.objects.filter(email=CEO_EMAIL).delete()

    # 2. Update existing owner account to mohdfaizanali038@gmail.com or create it
    owner = User.objects.filter(email=OLD_OWNER_EMAIL).first()
    if owner:
        owner.email = NEW_OWNER_EMAIL
        owner.first_name = "Faizan"
        owner.last_name = "Ali"
        owner.role = "owner"
        owner.is_staff = True
        owner.is_superuser = True
        owner.email_verified = True
        owner.is_active = True
        owner.password = make_password(OWNER_PASS)
        owner.save()
    else:
        owner, _ = User.objects.get_or_create(
            email=NEW_OWNER_EMAIL,
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
        owner.role = "owner"
        owner.is_staff = True
        owner.is_superuser = True
        owner.email_verified = True
        owner.is_active = True
        owner.password = make_password(OWNER_PASS)
        owner.save()

    # Ensure the old email is purged if separate
    User.objects.filter(email=OLD_OWNER_EMAIL).exclude(pk=owner.pk).delete()

    admin_group = Group.objects.filter(name="Admin").first()
    if admin_group:
        owner.groups.add(admin_group)


def revert_migration(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0008_owner_setup"),
    ]

    operations = [
        migrations.RunPython(update_owner_and_purge_ceo, revert_migration),
    ]
