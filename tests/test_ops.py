from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts.apps import assign_permissions
from apps.accounts.models import AuditLog, User
from apps.jobs.models import Application, Job


def make_staff(email, role):
    user = User.objects.create_user(email=email, password="test-pass-12345", is_staff=True)
    user.groups.add(Group.objects.get(name=role))
    return user


class AuditLogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()
        cls.recruiter = make_staff("r@example.com", "Recruiter")
        cls.candidate = User.objects.create_user(email="c@example.com", password="test-pass-12345")
        cls.job = Job.objects.create(title="Dev", location="x", description="x", published=True)
        cls.application = Application.objects.create(
            job=cls.job, applicant=cls.candidate, resume="resumes/x.pdf"
        )

    def test_status_change_is_recorded(self):
        self.client.force_login(self.recruiter)
        self.client.post(
            reverse("staff_application_status", args=[self.application.pk]),
            {"status": "shortlisted"},
        )
        entry = AuditLog.objects.get(action="application.status")
        self.assertEqual(entry.actor, self.recruiter)
        self.assertIn("shortlisted", entry.details)
        self.assertEqual(entry.ip, "127.0.0.1")


class TwoFactorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            email="s@example.com", password="test-pass-12345", is_staff=True
        )

    @staticmethod
    def _token(device):
        return totp(device.bin_key, device.step, device.t0, device.digits)

    @override_settings(REQUIRE_STAFF_2FA=True)
    def test_staff_pages_redirect_until_verified(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("security"), response.url)

    @override_settings(REQUIRE_STAFF_2FA=True)
    def test_enrol_then_access_is_allowed(self):
        self.client.force_login(self.staff)
        self.client.get(reverse("security"))  # creates the pending device
        device = TOTPDevice.objects.get(user=self.staff)
        response = self.client.post(
            reverse("security"), {"action": "enable", "token": self._token(device)}, follow=True
        )
        self.assertContains(response, "Two-factor authentication is active")
        device.refresh_from_db()
        self.assertTrue(device.confirmed)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_wrong_code_is_rejected(self):
        self.client.force_login(self.staff)
        self.client.get(reverse("security"))
        device = TOTPDevice.objects.get(user=self.staff)
        self.client.post(reverse("security"), {"action": "enable", "token": "000000"})
        device.refresh_from_db()
        self.assertFalse(device.confirmed)

    def test_non_staff_cannot_open_security(self):
        user = User.objects.create_user(email="n@example.com", password="test-pass-12345")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("security")).status_code, 403)


class BackupCommandTests(TestCase):
    def test_backup_writes_json(self):
        import tempfile
        from pathlib import Path

        from django.core.management import call_command

        User.objects.create_user(email="backup@example.com", password="test-pass-12345")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "backup.json"
            call_command("backup_db", output=str(target))
            self.assertTrue(target.exists())
            self.assertIn("accounts.user", target.read_text())
