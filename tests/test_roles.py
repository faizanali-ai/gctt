from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.apps import assign_permissions
from apps.accounts.models import User


def make_user(email, role, **extra):
    return User.objects.create_user(
        email=email, password="test-pass-12345", role=role, is_staff=True, **extra
    )


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RoleManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()
        cls.admin = User.objects.create_superuser(
            email="admin@example.com", password="test-pass-12345"
        )
        cls.staff = make_user("staff@example.com", User.Role.STAFF)
        cls.staff.groups.add(Group.objects.get(name="Recruiter"))

    def _create(self, email, role, group="Recruiter"):
        self.client.force_login(self.admin)
        return self.client.post(
            reverse("manage_user_create"),
            {
                "email": email,
                "first_name": "New",
                "last_name": "Person",
                "role": role,
                "group": group,
                "password": "temp-pass-12345",
            },
        )

    def test_admin_can_create_admin(self):
        response = self._create("new.admin@example.com", User.Role.ADMIN)
        self.assertRedirects(response, reverse("manage_users"))
        user = User.objects.get(email="new.admin@example.com")
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertTrue(user.is_superuser)
        self.assertEqual(list(user.groups.values_list("name", flat=True)), ["Admin"])

    def test_admin_can_create_staff_with_subgroup(self):
        self._create("new.staff@example.com", User.Role.STAFF, "Trainer")
        user = User.objects.get(email="new.staff@example.com")
        self.assertEqual(user.role, User.Role.STAFF)
        self.assertFalse(user.is_superuser)
        self.assertEqual(list(user.groups.values_list("name", flat=True)), ["Trainer"])

    def test_staff_requires_valid_subgroup(self):
        self._create("bad.group@example.com", User.Role.STAFF, "Admin")
        self.assertFalse(User.objects.filter(email="bad.group@example.com").exists())
        self._create("no.group@example.com", User.Role.STAFF, "")
        self.assertFalse(User.objects.filter(email="no.group@example.com").exists())

    def test_staff_cannot_open_user_management(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("manage_users")).status_code, 403)

    def test_create_form_requires_a_real_subgroup(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("manage_user_create"))
        self.assertContains(response, "Staff Subgroup")
        self.assertContains(response, "Recruiter")
        self.assertNotContains(response, "None (Read Only)")
        self.assertContains(response, 'id="subgroup-field"')

    def test_last_admin_cannot_demote_self(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse("manage_user_edit", args=[self.admin.pk]),
            {
                "first_name": "Admin",
                "last_name": "One",
                "role": User.Role.STAFF,
                "group": "Recruiter",
                "is_active": "on",
            },
        )
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, User.Role.ADMIN)

    def test_admin_can_deactivate_staff(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse("manage_user_edit", args=[self.staff.pk]),
            {
                "first_name": self.staff.first_name,
                "last_name": self.staff.last_name,
                "role": User.Role.STAFF,
                "group": "Recruiter",
            },
        )
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)


class PortalShellTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()
        cls.admin = User.objects.create_superuser(
            email="admin2@example.com", password="test-pass-12345"
        )
        cls.candidate = User.objects.create_user(
            email="cand@example.com", password="test-pass-12345"
        )

    def test_admin_sees_sidebar_and_can_manage_users(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Users &amp; roles")
        self.assertEqual(response.status_code, 200)

    def test_candidate_has_portal_without_staff_links(self):
        self.client.force_login(self.candidate)
        response = self.client.get(reverse("dashboard"))
        self.assertNotContains(response, "Users &amp; roles")
        self.assertNotContains(response, "staff_jobs")
