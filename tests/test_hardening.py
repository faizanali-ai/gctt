import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.jobs.models import Application, Job


class UploadHardeningTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.user = User.objects.create_user(email="u@example.com", password="test-pass-12345")
        self.job = Job.objects.create(title="Dev", location="x", description="x", published=True)
        self.client.force_login(self.user)

    def _post(self, filename, content):
        return self.client.post(
            reverse("job_apply", args=[self.job.slug]),
            {"resume": SimpleUploadedFile(filename, content), "message": "Keen"},
        )

    def test_pdf_with_non_pdf_content_is_rejected(self):
        response = self._post("cv.pdf", b"<script>alert(1)</script>")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Application.objects.exists())

    def test_valid_pdf_is_accepted_with_opaque_filename(self):
        self._post("my-resume.pdf", b"%PDF-1.4 fake but valid header")
        application = Application.objects.get()
        self.assertRegex(application.resume.name, r"^resumes/[0-9a-f]{32}\.pdf$")
        self.assertNotIn("my-resume", application.resume.name)

    def test_oversize_resume_is_rejected(self):
        response = self._post("big.pdf", b"%PDF-1.4" + b"0" * (6 * 1024 * 1024))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Application.objects.exists())


class AdminLoginThrottleTests(TestCase):
    def test_admin_login_is_rate_limited(self):
        payload = {"username": "nobody@example.com", "password": "wrong", "next": "/admin/"}
        for _ in range(10):
            self.client.post("/admin/login/", payload, REMOTE_ADDR="203.0.113.7")
        response = self.client.post("/admin/login/", payload, REMOTE_ADDR="203.0.113.7")
        self.assertEqual(response.status_code, 403)
