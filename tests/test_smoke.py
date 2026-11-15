from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.jobs.models import Application, Job
from apps.training.models import Programme


class SmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.job = Job.objects.create(
            title="SAP Consultant", location="Irving, TX", description="SAP role", published=True
        )
        cls.programme = Programme.objects.create(
            title="SAP Foundations", description="SAP training", published=True, registration_open=True
        )
        cls.user = User.objects.create_user(
            email="candidate@example.com", password="test-pass-12345", first_name="Ada"
        )

    def test_public_pages_return_200(self):
        urls = [
            "/", "/about/", "/services/", "/it-staffing/", "/recruitment/",
            "/talent-acquisition/", "/sap-scrum/", "/career-restart/", "/employers/",
            "/contact/", "/privacy/", "/terms/", "/careers/", "/training/",
            f"/careers/{self.job.slug}/", f"/training/{self.programme.slug}/",
            "/accounts/login/", "/accounts/signup/", "/accounts/password-reset/",
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_healthz(self):
        response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_healthz_reports_database_failure(self):
        from unittest.mock import patch

        from django.db import OperationalError

        with patch(
            "config.views.connection.cursor", side_effect=OperationalError("down")
        ):
            response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 503)

    def test_home_has_skip_link(self):
        self.assertContains(self.client.get("/"), "Skip to content")

    def test_slug_collisions_get_suffix(self):
        first = Job.objects.create(title="Duplicate Title", location="x", description="x")
        second = Job.objects.create(title="Duplicate Title", location="x", description="x")
        self.assertEqual(first.slug, "duplicate-title")
        self.assertEqual(second.slug, "duplicate-title-2")

    def test_apply_rejects_bad_extension(self):
        self.client.force_login(self.user)
        from django.core.files.uploadedfile import SimpleUploadedFile

        response = self.client.post(
            reverse("job_apply", args=[self.job.slug]),
            {"resume": SimpleUploadedFile("cv.exe", b"nope")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Application.objects.exists())

    def test_duplicate_application_is_handled(self):
        self.client.force_login(self.user)
        Application.objects.create(job=self.job, applicant=self.user, resume="resumes/x.pdf")
        from django.core.files.uploadedfile import SimpleUploadedFile

        response = self.client.post(
            reverse("job_apply", args=[self.job.slug]),
            {
                "resume": SimpleUploadedFile("cv.pdf", b"%PDF-1.4"),
                "message": "I'm keen",
            },
            follow=True,
        )
        self.assertEqual(Application.objects.count(), 1)
        self.assertContains(response, "already applied")

    def test_enquiry_form_saves(self):
        response = self.client.post(
            reverse("submit_enquiry"),
            {
                "name": "Test",
                "email": "test@example.com",
                "category": "general",
                "message": "Hello",
                "next": "contact",
            },
        )
        self.assertRedirects(response, reverse("contact"))
        self.assertEqual(self.client.get(reverse("contact")).status_code, 200)
