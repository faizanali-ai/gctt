from io import StringIO

from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.accounts.apps import assign_permissions
from apps.accounts.models import User


class AuditAccessCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()

    def setUp(self):
        User.objects.all().delete()
        self.admin = User.objects.create_superuser(
            email="admin@example.com", password="test-pass-12345"
        )
        self.staff = User.objects.create_user(
            email="staff@example.com",
            password="test-pass-12345",
            role=User.Role.STAFF,
            is_staff=True,
        )
        self.staff.groups.add(Group.objects.get(name="Recruiter"))
        self.candidate = User.objects.create_user(
            email="candidate@example.com",
            password="test-pass-12345",
            account_type=User.AccountType.CANDIDATE,
        )
        self.student = User.objects.create_user(
            email="student@example.com",
            password="test-pass-12345",
            account_type=User.AccountType.STUDENT,
        )

    def run_command(self, *args):
        output = StringIO()
        call_command("audit_access", *args, stdout=output)
        return output.getvalue()

    def test_clean_state(self):
        output = self.run_command("--strict")
        self.assertIn("No access issues found.", output)
        self.assertIn("Admins: 1 active / 1 total", output)
        self.assertIn("Recruiter=1", output)
        self.assertIn("Candidates: 1", output)
        self.assertIn("Students: 1", output)

    def test_anomalies_are_reported_and_strict_fails(self):
        User.objects.create_user(
            email="no.subgroup@example.com",
            password="test-pass-12345",
            role=User.Role.STAFF,
            is_staff=True,
        )
        multi = User.objects.create_user(
            email="multi@example.com",
            password="test-pass-12345",
            role=User.Role.STAFF,
            is_staff=True,
        )
        multi.groups.add(
            Group.objects.get(name="Recruiter"), Group.objects.get(name="Trainer")
        )
        admin_group = User.objects.create_user(
            email="admin.group@example.com",
            password="test-pass-12345",
            role=User.Role.STAFF,
            is_staff=True,
        )
        admin_group.groups.add(Group.objects.get(name="Admin"))
        super_staff = User.objects.create_user(
            email="super.staff@example.com",
            password="test-pass-12345",
            role=User.Role.STAFF,
            is_staff=True,
            is_superuser=True,
        )
        super_staff.groups.add(Group.objects.get(name="Recruiter"))
        direct = User.objects.create_user(
            email="direct@example.com",
            password="test-pass-12345",
            role=User.Role.STAFF,
            is_staff=True,
        )
        direct.groups.add(Group.objects.get(name="Recruiter"))
        direct.user_permissions.add(
            Permission.objects.get(codename="view_application")
        )
        external_group = User.objects.create_user(
            email="external.group@example.com", password="test-pass-12345"
        )
        external_group.groups.add(Group.objects.get(name="Trainer"))
        User.objects.create_user(
            email="external.super@example.com",
            password="test-pass-12345",
            is_superuser=True,
        )
        User.objects.create_user(
            email="bad.admin@example.com",
            password="test-pass-12345",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        User.objects.create_user(
            email="bad.role@example.com",
            password="test-pass-12345",
            role="owner",
            is_staff=True,
        )
        User.objects.create_user(
            email="bad.external@example.com",
            password="test-pass-12345",
            account_type="unknown",
        )

        before = (
            User.objects.count(),
            Group.objects.count(),
            sum(u.user_permissions.count() for u in User.objects.all()),
        )
        output = self.run_command()
        after = (
            User.objects.count(),
            Group.objects.count(),
            sum(u.user_permissions.count() for u in User.objects.all()),
        )
        self.assertEqual(before, after)
        self.assertIn("no.subgroup@example.com: no staff subgroup", output)
        self.assertIn("multi@example.com: multiple subgroups", output)
        self.assertIn("admin.group@example.com: unexpected groups ['Admin']", output)
        self.assertIn("super.staff@example.com: is_superuser=True", output)
        self.assertIn("direct@example.com: direct user permissions present", output)
        self.assertIn("external.group@example.com: groups ['Trainer']", output)
        self.assertIn("external.super@example.com: is_superuser=True", output)
        self.assertIn("bad.admin@example.com: missing Admin group", output)
        self.assertIn("bad.admin@example.com: role=admin but is_superuser=False", output)
        self.assertIn("bad.role@example.com: invalid role='owner'", output)
        self.assertIn("bad.external@example.com: invalid account_type", output)
        self.assertIn("Issues:", output)
        with self.assertRaises(CommandError):
            self.run_command("--strict")


