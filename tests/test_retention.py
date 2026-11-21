import os
import shutil
import tempfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog, User
from apps.jobs.models import Application, Job
from apps.training.models import Programme, Registration


class PurgeRetentionTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)

        self.student = User.objects.create_user(
            email="student@example.com", password="test-pass-12345"
        )
        self.student_two = User.objects.create_user(
            email="student2@example.com", password="test-pass-12345"
        )
        self.job = Job.objects.create(
            title="Engineer", location="Remote", description="x", published=True
        )
        self.programme = Programme.objects.create(
            title="SAP", description="x", published=True
        )
        self.old_application = Application.objects.create(
            job=self.job,
            applicant=self.student,
            resume=SimpleUploadedFile("cv.pdf", b"resume"),
            message="old",
        )
        self.old_uncertified = Registration.objects.create(
            programme=self.programme, student=self.student, message="old"
        )
        self.old_certified = Registration.objects.create(
            programme=self.programme,
            student=self.student_two,
            certificate_issued=True,
            certificate_ref="GCTT-OLD",
            message="keep the certificate, clear this",
        )
        self.old_audit = AuditLog.objects.create(action="user.login", target="student")

        old = timezone.now() - timedelta(days=800)
        Application.objects.filter(pk=self.old_application.pk).update(created_at=old)
        Registration.objects.filter(pk=self.old_uncertified.pk).update(created_at=old)
        Registration.objects.filter(pk=self.old_certified.pk).update(created_at=old)
        AuditLog.objects.filter(pk=self.old_audit.pk).update(created_at=old)

    def test_dry_run_changes_nothing(self):
        call_command("purge_retention")
        self.assertTrue(Application.objects.filter(pk=self.old_application.pk).exists())
        self.assertTrue(Registration.objects.filter(pk=self.old_uncertified.pk).exists())
        self.assertTrue(AuditLog.objects.filter(pk=self.old_audit.pk).exists())
        self.assertTrue(Application.objects.get(pk=self.old_application.pk).resume)

    def test_apply_deletes_and_clears_as_recorded(self):
        resume_path = self.old_application.resume.path
        call_command("purge_retention", "--apply")

        self.assertFalse(Application.objects.filter(pk=self.old_application.pk).exists())
        self.assertFalse(Registration.objects.filter(pk=self.old_uncertified.pk).exists())
        certified = Registration.objects.get(pk=self.old_certified.pk)
        self.assertEqual(certified.message, "")
        self.assertTrue(AuditLog.objects.filter(pk=self.old_audit.pk).exists())
        self.assertFalse(os.path.exists(resume_path))

    def test_recent_records_survive(self):
        recent = Application.objects.create(
            job=self.job,
            applicant=self.student_two,
            resume=SimpleUploadedFile("new.pdf", b"x"),
        )
        call_command("purge_retention", "--apply")
        self.assertTrue(Application.objects.filter(pk=recent.pk).exists())
