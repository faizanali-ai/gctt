from importlib import import_module

from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.test import TestCase

from apps.accounts.apps import assign_permissions
from apps.accounts.models import User

role_migration = import_module("apps.accounts.migrations.0010_consolidate_roles")


class ConsolidateRolesMigrationTests(TestCase):
    def setUp(self):
        assign_permissions()
        # Isolate from the owner seeded by migrations 0008/0009.
        User.objects.all().delete()
        self.admin_group = Group.objects.get(name="Admin")

        self.owner = User.objects.create_user(
            email="migration.owner@example.com",
            password="test-pass-12345",
            role="owner",
            is_staff=True,
            is_superuser=True,
        )
        self.owner.groups.add(self.admin_group)

        self.superadmin = User.objects.create_user(
            email="migration.superadmin@example.com",
            password="test-pass-12345",
            role="superadmin",
            is_staff=True,
        )
        self.ceo = User.objects.create_user(
            email="migration.ceo@example.com",
            password="test-pass-12345",
            role="ceo",
            is_staff=True,
        )
        self.staff = User.objects.create_user(
            email="migration.staff@example.com",
            password="test-pass-12345",
            role="staff",
            is_staff=True,
        )
        self.staff.groups.add(Group.objects.get(name="Recruiter"))

        self.external = User.objects.create_user(
            email="migration.external@example.com",
            password="test-pass-12345",
            account_type=User.AccountType.CANDIDATE,
        )
        self.external.is_staff = False
        self.external.save(update_fields=["is_staff"])
        self.external.groups.add(Group.objects.get(name="Trainer"))
        self.external.user_permissions.add(
            Permission.objects.get(codename="view_application")
        )

    def test_forward_merges_all_top_level_roles_and_reverse_restores_no_lockout(self):
        with self.assertLogs(
            "apps.accounts.migrations.0010_consolidate_roles", level="WARNING"
        ) as logs:
            role_migration.consolidate(apps, None)

        self.owner.refresh_from_db()
        self.superadmin.refresh_from_db()
        self.ceo.refresh_from_db()
        self.staff.refresh_from_db()
        self.external.refresh_from_db()

        for top_level in (self.owner, self.superadmin, self.ceo):
            self.assertEqual(top_level.role, "admin")
            self.assertTrue(top_level.is_staff)
            self.assertTrue(top_level.is_superuser)
            self.assertEqual(
                list(top_level.groups.values_list("name", flat=True)), ["Admin"]
            )

        self.assertEqual(self.staff.role, "staff")
        self.assertFalse(self.staff.is_superuser)
        self.assertEqual(
            list(self.staff.groups.values_list("name", flat=True)), ["Recruiter"]
        )

        self.assertEqual(self.external.role, "staff")
        self.assertEqual(self.external.groups.count(), 0)
        self.assertEqual(self.external.user_permissions.count(), 0)
        self.assertTrue(any("Cleared group memberships" in line for line in logs.output))

        role_migration.restore_legacy(apps, None)

        self.owner.refresh_from_db()
        self.superadmin.refresh_from_db()
        self.ceo.refresh_from_db()
        self.assertEqual(self.owner.role, "owner")
        self.assertEqual(self.superadmin.role, "superadmin")
        self.assertEqual(self.ceo.role, "superadmin")
        self.assertTrue(self.owner.is_superuser)
        self.assertEqual(
            list(self.owner.groups.values_list("name", flat=True)), ["Admin"]
        )

        # Re-applying the forward step must not leave the system without an admin.
        role_migration.consolidate(apps, None)
        self.assertTrue(
            User.objects.filter(role="admin", is_active=True, is_staff=True).exists()
        )
