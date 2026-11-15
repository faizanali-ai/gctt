from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.apps import assign_permissions
from apps.accounts.models import User


def make_user(email, role, **extra):
    user = User.objects.create_user(
        email=email, password="test-pass-12345", role=role, is_staff=True, **extra
    )
    return user


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RoleManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()
        cls.owner = make_user("owner@example.com", User.Role.OWNER, is_superuser=True)
        cls.superadmin = make_user("super@example.com", User.Role.SUPERADMIN)
        cls.ceo = make_user("ceo@example.com", User.Role.CEO)
        cls.staff = make_user("staff@example.com", User.Role.STAFF)
        cls.staff.groups.add(Group.objects.get(name="Recruiter"))

    def _create(self, actor, email, role):
        self.client.force_login(actor)
        return self.client.post(
            reverse("manage_user_create"),
            {
                "email": email,
                "first_name": "New",
                "last_name": "Person",
                "role": role,
                "group": "Recruiter",
                "password": "temp-pass-12345",
            },
        )

    def test_owner_can_create_superadmin(self):
        response = self._create(self.owner, "new.super@example.com", User.Role.SUPERADMIN)
        self.assertRedirects(response, reverse("manage_users"))
        user = User.objects.get(email="new.super@example.com")
        self.assertEqual(user.role, User.Role.SUPERADMIN)
        self.assertTrue(user.is_staff)

    def test_superadmin_cannot_create_superadmin(self):
        self._create(self.superadmin, "nope@example.com", User.Role.SUPERADMIN)
        self.assertFalse(User.objects.filter(email="nope@example.com").exists())

    def test_ceo_can_create_staff_but_not_superadmin(self):
        self._create(self.ceo, "ok.staff@example.com", User.Role.STAFF)
        self.assertTrue(User.objects.filter(email="ok.staff@example.com").exists())
        self._create(self.ceo, "bad.super@example.com", User.Role.SUPERADMIN)
        self.assertFalse(User.objects.filter(email="bad.super@example.com").exists())

    def test_staff_cannot_open_user_management(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("manage_users")).status_code, 403)

    def test_superadmin_cannot_edit_owner(self):
        self.client.force_login(self.superadmin)
        response = self.client.get(reverse("manage_user_edit", args=[self.owner.pk]))
        self.assertEqual(response.status_code, 404)

    def test_ceo_cannot_edit_superadmin(self):
        self.client.force_login(self.ceo)
        response = self.client.get(reverse("manage_user_edit", args=[self.superadmin.pk]))
        self.assertEqual(response.status_code, 403)

    def test_owner_can_deactivate_staff(self):
        self.client.force_login(self.owner)
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
        cls.ceo = make_user("ceo2@example.com", User.Role.CEO)
        cls.candidate = User.objects.create_user(
            email="cand@example.com", password="test-pass-12345"
        )

    def test_ceo_sees_sidebar_and_can_manage_users(self):
        self.client.force_login(self.ceo)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Users &amp; roles")
        self.assertEqual(response.status_code, 200)

    def test_candidate_has_portal_without_staff_links(self):
        self.client.force_login(self.candidate)
        response = self.client.get(reverse("dashboard"))
        self.assertNotContains(response, "Users &amp; roles")
        self.assertNotContains(response, "staff_jobs")
