import logging

from django.db import migrations, models

STAFF_SUBGROUPS = ("Recruiter", "Trainer", "Enquiry Manager")

logger = logging.getLogger(__name__)


def _subgroup(user):
    names = set(user.groups.values_list("name", flat=True))
    return next((name for name in STAFF_SUBGROUPS if name in names), None)


def _set_staff_access(user, Group, role_label):
    subgroup = _subgroup(user)
    if subgroup:
        group, _ = Group.objects.get_or_create(name=subgroup)
        user.groups.set([group])
    else:
        logger.warning(
            "Cleared group memberships for %s (legacy role=%s, no staff subgroup)",
            user.email,
            role_label,
        )
        user.groups.clear()


def consolidate(apps, schema_editor):
    """Policy: owner, superadmin, CEO and admin merge into the admin role."""
    User = apps.get_model("accounts", "User")
    Group = apps.get_model("auth", "Group")

    admin_group, _ = Group.objects.get_or_create(name="Admin")

    for user in User.objects.all().iterator():
        legacy_role = user.role

        if legacy_role in ("owner", "admin", "superadmin", "ceo"):
            user.role = "admin"
            user.is_staff = True
            user.is_superuser = True
            user.save(update_fields=["role", "is_staff", "is_superuser"])
            user.groups.set([admin_group])
        elif user.is_staff:
            user.role = "staff"
            user.is_superuser = False
            user.save(update_fields=["role", "is_superuser"])
            _set_staff_access(user, Group, legacy_role)
        else:
            user.role = "staff"
            user.is_superuser = False
            user.save(update_fields=["role", "is_superuser"])
            if user.groups.exists():
                logger.warning(
                    "Cleared group memberships for %s (external account)", user.email
                )
            user.groups.clear()

        # Groups are the single source of truth going forward.
        user.user_permissions.clear()


def restore_legacy(apps, schema_editor):
    """Restore a usable legacy hierarchy: first admin -> owner, rest -> superadmin."""
    User = apps.get_model("accounts", "User")
    Group = apps.get_model("auth", "Group")

    admin_group = Group.objects.filter(name="Admin").first()
    admins = list(User.objects.filter(role="admin").order_by("pk"))

    if not admins:
        logger.critical("Reverse 0010 found no admin rows; legacy rollback has no owner.")
    else:
        for index, user in enumerate(admins):
            user.role = "owner" if index == 0 else "superadmin"
            user.is_staff = True
            user.is_superuser = True
            user.save(update_fields=["role", "is_staff", "is_superuser"])
            if admin_group:
                user.groups.set([admin_group])

    User.objects.filter(role="staff").update(is_superuser=False)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0009_owner_update_and_remove_ceo"),
    ]

    operations = [
        migrations.RunPython(consolidate, restore_legacy),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[("admin", "Admin"), ("staff", "Staff")],
                default="staff",
                max_length=20,
            ),
        ),
    ]
