from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.apps import assign_permissions
from apps.accounts.models import AuditLog, User
from apps.jobs.models import Application, Job


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AccountSecurityPageTests(TestCase):
    def test_candidate_can_open_security_page(self):
        candidate = User.objects.create_user(
            email="cand2fa@example.com", password="test-pass-12345"
        )
        self.client.force_login(candidate)
        response = self.client.get(reverse("security"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Account Security")
        self.assertNotContains(response, "Two-Factor Authentication")


class PasswordResetRateLimitTests(TestCase):
    def test_sixth_post_is_blocked(self):
        url = reverse("password_reset")
        for _ in range(5):
            response = self.client.post(
                url, {"email": "nobody@example.com"}, REMOTE_ADDR="198.51.100.55"
            )
            self.assertNotEqual(response.status_code, 403)
        response = self.client.post(
            url, {"email": "nobody@example.com"}, REMOTE_ADDR="198.51.100.55"
        )
        self.assertEqual(response.status_code, 403)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class StaffPasswordValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()
        cls.owner = User.objects.create_user(
            email="owner2@example.com",
            password="test-pass-12345",
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )

    def test_weak_password_is_rejected_on_create(self):
        self.client.force_login(self.owner)
        self.client.post(
            reverse("manage_user_create"),
            {
                "email": "weak@example.com",
                "first_name": "Weak",
                "last_name": "Pass",
                "role": User.Role.STAFF,
                "group": "Recruiter",
                "password": "12345678",
            },
        )
        self.assertFalse(User.objects.filter(email="weak@example.com").exists())

    def test_common_password_is_rejected_on_edit(self):
        target = User.objects.create_user(
            email="editme@example.com", password="test-pass-12345", role=User.Role.STAFF, is_staff=True
        )
        self.client.force_login(self.owner)
        self.client.post(
            reverse("manage_user_edit", args=[target.pk]),
            {
                "first_name": "Edit",
                "last_name": "Me",
                "role": User.Role.STAFF,
                "group": "Recruiter",
                "is_active": "on",
                "password": "password123",
            },
        )
        target.refresh_from_db()
        self.assertTrue(target.check_password("test-pass-12345"))

    def test_strong_password_is_accepted_on_edit(self):
        target = User.objects.create_user(
            email="strong@example.com", password="test-pass-12345", role=User.Role.STAFF, is_staff=True
        )
        self.client.force_login(self.owner)
        self.client.post(
            reverse("manage_user_edit", args=[target.pk]),
            {
                "first_name": "Strong",
                "last_name": "Pass",
                "role": User.Role.STAFF,
                "group": "Recruiter",
                "is_active": "on",
                "password": "Zx7!mQ2#vL9$pR4",
            },
        )
        target.refresh_from_db()
        self.assertTrue(target.check_password("Zx7!mQ2#vL9$pR4"))


class AccountDeletionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.candidate = User.objects.create_user(
            email="delete-me@example.com", password="test-pass-12345"
        )
        cls.job = Job.objects.create(title="Role", location="x", description="x", published=True)
        cls.application = Application.objects.create(
            job=cls.job, applicant=cls.candidate, resume="resumes/x.pdf"
        )
        cls.owner = User.objects.create_user(
            email="owner-del@example.com",
            password="test-pass-12345",
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )

    def test_wrong_password_keeps_account(self):
        self.client.force_login(self.candidate)
        response = self.client.post(
            reverse("account_delete"), {"password": "wrong-password"}, follow=True
        )
        self.assertContains(response, "Password incorrect")
        self.assertTrue(User.objects.filter(email="delete-me@example.com").exists())

    def test_correct_password_deletes_account_and_data(self):
        self.client.force_login(self.candidate)
        response = self.client.post(
            reverse("account_delete"), {"password": "test-pass-12345"}
        )
        self.assertRedirects(response, reverse("home"))
        self.assertFalse(User.objects.filter(email="delete-me@example.com").exists())
        self.assertFalse(Application.objects.filter(applicant_id=self.candidate.pk).exists())
        entry = AuditLog.objects.get(action="account.delete")
        self.assertEqual(entry.target, "delete-me@example.com")

    def test_owner_cannot_delete_self(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("account_delete"), {"password": "test-pass-12345"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(email="owner-del@example.com").exists())
