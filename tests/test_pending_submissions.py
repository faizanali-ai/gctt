import os
import re
import shutil
import tempfile
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.pending import hash_token
from apps.jobs.models import Application, Job, PendingApplication
from apps.training.models import PendingRegistration, Programme, Registration

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


@override_settings(EMAIL_BACKEND=LOCMEM)
class PendingSubmissionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
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
        self.job = Job.objects.create(
            title="Platform Engineer", location="Remote", description="x", published=True
        )
        self.programme = Programme.objects.create(
            title="SAP Basics", description="x", published=True, registration_open=True
        )

    def _token(self, prefix):
        message = next(m for m in mail.outbox if prefix in m.body)
        return re.search(rf"{prefix}([^\s/]+)/", message.body).group(1)

    def _apply(self, email="candidate@example.com"):
        return self.client.post(
            reverse("job_apply", args=[self.job.slug]),
            {
                "first_name": "A",
                "last_name": "B",
                "email": email,
                "message": "I am keen",
                "resume": SimpleUploadedFile("cv.pdf", b"%PDF-1.4"),
            },
        )

    def _register(self, email="student@example.com"):
        return self.client.post(
            reverse("programme_register", args=[self.programme.slug]),
            {"full_name": "A B", "email": email, "message": "Please enroll"},
        )

    def test_existing_email_application_confirms_after_magic_link(self):
        response = self._apply()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Application.objects.exists())
        pending = PendingApplication.objects.get(email=self.candidate.email)
        self.assertNotIn("_auth_user_id", self.client.session)

        token = self._token("/careers/pending/")
        response = self.client.get(reverse("pending_application", args=[token]))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.candidate.refresh_from_db()
        self.assertIsNone(self.candidate.welcome_email_sent_at)
        self.assertFalse(
            any("Welcome" in message.subject for message in mail.outbox)
        )

        response = self.client.post(
            reverse("pending_application", args=[token]),
            {"message": "Confirmed message"},
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertIn("_auth_user_id", self.client.session)
        self.candidate.refresh_from_db()
        self.assertTrue(self.candidate.email_verified)
        self.assertIsNotNone(self.candidate.welcome_email_sent_at)
        self.assertTrue(
            any("Welcome" in message.subject for message in mail.outbox)
        )
        application = Application.objects.get(job=self.job, applicant=self.candidate)
        self.assertEqual(application.message, "Confirmed message")
        self.assertTrue(application.resume.name.startswith("resumes/"))
        pending.refresh_from_db()
        self.assertIsNotNone(pending.consumed_at)

    def test_existing_email_registration_confirms_after_magic_link(self):
        self._register()
        self.assertFalse(Registration.objects.exists())
        pending = PendingRegistration.objects.get(email=self.student.email)
        token = self._token("/training/pending/")

        response = self.client.get(reverse("pending_registration", args=[token]))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.student.refresh_from_db()
        self.assertIsNone(self.student.welcome_email_sent_at)

        response = self.client.post(
            reverse("pending_registration", args=[token]),
            {"message": "Confirmed registration"},
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertIn("_auth_user_id", self.client.session)
        self.student.refresh_from_db()
        self.assertTrue(self.student.email_verified)
        self.assertIsNotNone(self.student.welcome_email_sent_at)
        registration = Registration.objects.get(
            programme=self.programme, student=self.student
        )
        self.assertEqual(registration.message, "Confirmed registration")
        pending.refresh_from_db()
        self.assertIsNotNone(pending.consumed_at)

    def test_used_and_expired_links_return_404(self):
        self._apply()
        token = self._token("/careers/pending/")
        pending = PendingApplication.objects.get()
        pending.consumed_at = timezone.now()
        pending.save(update_fields=["consumed_at"])
        response = self.client.get(reverse("pending_application", args=[token]))
        self.assertEqual(response.status_code, 404)

        expired = PendingApplication.objects.create(
            job=self.job,
            email=self.candidate.email,
            resume=SimpleUploadedFile("cv.pdf", b"%PDF-1.4"),
            message="x",
            token_hash=hash_token("expired-token"),
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        response = self.client.get(
            reverse("pending_application", args=["expired-token"])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(PendingApplication.objects.filter(pk=expired.pk).exists())

    def test_purge_pending_removes_expired_file(self):
        pending = PendingApplication.objects.create(
            job=self.job,
            email=self.candidate.email,
            resume=SimpleUploadedFile("cv.pdf", b"%PDF-1.4"),
            message="x",
            token_hash=hash_token("purge-token"),
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        path = pending.resume.path
        name = pending.resume.name
        self.assertTrue(os.path.exists(path))
        out = StringIO()
        with (
            patch.object(
                default_storage, "delete", wraps=default_storage.delete
            ) as mock_delete,
            self.captureOnCommitCallbacks(execute=True),
        ):
            call_command("purge_pending", stdout=out)
        self.assertFalse(PendingApplication.objects.filter(pk=pending.pk).exists())
        self.assertFalse(os.path.exists(path))
        mock_delete.assert_called_once_with(name)
        self.assertIn("Purged 1 pending application(s), 0 pending registration(s), 1 temp resume(s).", out.getvalue())

    def test_purge_pending_preserves_file_referenced_by_application(self):
        pending = PendingApplication.objects.create(
            job=self.job,
            email=self.candidate.email,
            resume=SimpleUploadedFile("cv.pdf", b"%PDF-1.4"),
            message="x",
            token_hash=hash_token("shared-token"),
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        Application.objects.create(
            job=self.job,
            applicant=self.candidate,
            resume=pending.resume.name,
            message="confirmed",
        )
        path = pending.resume.path
        out = StringIO()
        with self.captureOnCommitCallbacks(execute=True):
            call_command("purge_pending", stdout=out)
        self.assertFalse(PendingApplication.objects.filter(pk=pending.pk).exists())
        self.assertTrue(os.path.exists(path))
        self.assertIn("0 temp resume(s).", out.getvalue())

    def test_missing_subgroup_does_not_email_admin(self):
        admin = User.objects.create_superuser(
            email="admin@example.com", password="test-pass-12345"
        )
        mail.outbox.clear()
        self._apply(email="new.candidate@example.com")
        recipients = [address for message in mail.outbox for address in message.to]
        self.assertNotIn(admin.email, recipients)

    def test_link_for_another_authenticated_user_is_hidden(self):
        self._apply()
        token = self._token("/careers/pending/")
        self.client.force_login(self.student)
        response = self.client.get(reverse("pending_application", args=[token]))
        self.assertEqual(response.status_code, 404)


    def test_staff_pending_link_does_not_log_in(self):
        staff = User.objects.create_user(
            email="staff-member@example.com",
            password="test-pass-12345",
            is_staff=True,
            role=User.Role.STAFF,
        )
        pending = PendingApplication.objects.create(
            job=self.job,
            email=staff.email,
            resume=SimpleUploadedFile("cv.pdf", b"%PDF-1.4"),
            message="x",
            token_hash=hash_token("staff-pending-token"),
            expires_at=timezone.now() + timedelta(hours=1),
        )
        response = self.client.get(
            reverse("pending_application", args=["staff-pending-token"])
        )
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(PendingApplication.objects.filter(pk=pending.pk).exists())

    def test_new_student_registration_waits_for_email_confirmation(self):
        response = self._register(email="new.student@example.com")
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Registration.objects.filter(student__email="new.student@example.com").exists()
        )
        pending = PendingRegistration.objects.get(email="new.student@example.com")
        token = self._token("/training/pending/")
        response = self.client.get(reverse("pending_registration", args=[token]))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.post(
            reverse("pending_registration", args=[token]), {"message": "confirmed"}
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertIn("_auth_user_id", self.client.session)
        self.assertTrue(
            Registration.objects.filter(
                programme=self.programme,
                student__email="new.student@example.com",
            ).exists()
        )
        pending.refresh_from_db()
        self.assertIsNotNone(pending.consumed_at)

    def test_new_candidate_application_waits_for_email_confirmation(self):
        response = self._apply(email="new.candidate.confirm@example.com")
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Application.objects.filter(
                applicant__email="new.candidate.confirm@example.com"
            ).exists()
        )
        pending = PendingApplication.objects.get(
            email="new.candidate.confirm@example.com"
        )
        candidate = User.objects.get(email="new.candidate.confirm@example.com")
        self.assertFalse(candidate.email_verified)
        token = self._token("/careers/pending/")
        get_resp = self.client.get(reverse("pending_application", args=[token]))
        self.assertEqual(get_resp.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        post_resp = self.client.post(
            reverse("pending_application", args=[token]), {"message": "confirmed"}
        )
        self.assertRedirects(post_resp, reverse("dashboard"))
        self.assertIn("_auth_user_id", self.client.session)
        candidate.refresh_from_db()
        self.assertTrue(candidate.email_verified)
        self.assertTrue(
            Application.objects.filter(
                job=self.job, applicant=candidate
            ).exists()
        )
        pending.refresh_from_db()
        self.assertIsNotNone(pending.consumed_at)

    def test_pending_application_storage_failure_releases_cooldown_and_retries(self):
        cooldown_key = f"pending-application:{self.job.pk}:guest.retry@example.com"
        payload = {
            "first_name": "A",
            "last_name": "B",
            "email": "guest.retry@example.com",
            "message": "I am keen",
        }
        with patch.object(
            PendingApplication.objects, "create", side_effect=OSError("storage down")
        ):
            response = self.client.post(
                reverse("job_apply", args=[self.job.slug]),
                {**payload, "resume": SimpleUploadedFile("cv.pdf", b"%PDF-1.4")},
                follow=True,
            )
        self.assertRedirects(response, reverse("job_detail", args=[self.job.slug]))
        self.assertIsNone(cache.get(cooldown_key))
        self.assertContains(response, "store your application just now")

        retry_resp = self._apply(email="guest.retry@example.com")
        self.assertRedirects(retry_resp, reverse("job_detail", args=[self.job.slug]))
        self.assertTrue(
            PendingApplication.objects.filter(
                job=self.job, email="guest.retry@example.com"
            ).exists()
        )
        self.assertIsNotNone(cache.get(cooldown_key))

    def test_pending_application_email_failure_clears_cooldown_but_keeps_row(self):
        cooldown_key = f"pending-application:{self.job.pk}:mail.fail@example.com"
        with patch("config.emails.send", return_value=0):
            response = self._apply(email="mail.fail@example.com")
        self.assertRedirects(response, reverse("job_detail", args=[self.job.slug]))
        self.assertTrue(
            PendingApplication.objects.filter(
                job=self.job, email="mail.fail@example.com"
            ).exists()
        )
        self.assertIsNone(cache.get(cooldown_key))

    def test_pending_application_email_prep_exception_releases_cooldown_and_retries(self):
        email = "prep.boom@example.com"
        cooldown_key = f"pending-application:{self.job.pk}:{email}"
        with patch(
            "apps.jobs.views.send_pending_application",
            side_effect=RuntimeError("template render boom"),
        ):
            response = self._apply(email=email)
        self.assertRedirects(response, reverse("job_detail", args=[self.job.slug]))
        self.assertTrue(
            PendingApplication.objects.filter(job=self.job, email=email).exists()
        )
        self.assertIsNone(cache.get(cooldown_key))

        retry_resp = self._apply(email=email)
        self.assertRedirects(retry_resp, reverse("job_detail", args=[self.job.slug]))
        self.assertEqual(
            PendingApplication.objects.filter(job=self.job, email=email).count(), 2
        )
        self.assertIsNotNone(cache.get(cooldown_key))
