from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

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
            reverse("staff_application_status", args=[self.application.uuid]),
            {"status": "shortlisted"},
        )
        entry = AuditLog.objects.get(action="application.status")
        self.assertEqual(entry.actor, self.recruiter)
        self.assertIn("shortlisted", entry.details)
        self.assertEqual(entry.ip, "127.0.0.1")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_status_change_emails_the_candidate(self):
        from django.core import mail

        self.client.force_login(self.recruiter)
        self.client.post(
            reverse("staff_application_status", args=[self.application.uuid]),
            {"status": "shortlisted"},
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["c@example.com"])
        self.assertIn("shortlisted", mail.outbox[0].subject.lower())


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
