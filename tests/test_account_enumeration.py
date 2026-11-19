from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.jobs.models import Application, Job
from apps.training.models import Programme, Registration

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


@override_settings(EMAIL_BACKEND=LOCMEM)
class EnumerationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.existing = User.objects.create_user(
            email="existing@example.com", password="test-pass-12345"
        )

    def test_signup_response_is_identical_for_existing_email(self):
        payload = {
            "account_type": "candidate",
            "email": "existing@example.com",
            "first_name": "Existing",
            "last_name": "Person",
            "password1": "test-pass-12345",
            "password2": "test-pass-12345",
        }
        response = self.client.post(reverse("signup"), payload, follow=True)
        self.assertNotContains(response, "already exists")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(User.objects.filter(email="existing@example.com").count(), 1)
        self.assertTrue(mail.outbox)

    def test_guest_apply_response_is_identical_for_existing_email(self):
        job_existing = Job.objects.create(
            title="Existing Role", location="x", description="x", published=True
        )
        job_new = Job.objects.create(
            title="New Role", location="x", description="x", published=True
        )
        resume = SimpleUploadedFile("cv.pdf", b"%PDF-1.4")
        existing_response = self.client.post(
            reverse("job_apply", args=[job_existing.slug]),
            {
                "first_name": "A",
                "last_name": "B",
                "email": self.existing.email,
                "message": "x",
                "resume": resume,
            },
        )
        resume = SimpleUploadedFile("cv.pdf", b"%PDF-1.4")
        new_response = self.client.post(
            reverse("job_apply", args=[job_new.slug]),
            {
                "first_name": "A",
                "last_name": "B",
                "email": "brand-new@example.com",
                "message": "x",
                "resume": resume,
            },
        )
        self.assertEqual(existing_response.status_code, 302)
        self.assertEqual(new_response.status_code, 302)
        self.assertEqual(existing_response.url, reverse("job_detail", args=[job_existing.slug]))
        self.assertEqual(new_response.url, reverse("job_detail", args=[job_new.slug]))
        self.assertFalse(Application.objects.filter(applicant=self.existing).exists())
        self.assertTrue(Application.objects.filter(applicant__email="brand-new@example.com").exists())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_guest_registration_response_is_identical_for_existing_email(self):
        programme_existing = Programme.objects.create(
            title="Existing Programme", description="x", published=True, registration_open=True
        )
        programme_new = Programme.objects.create(
            title="New Programme", description="x", published=True, registration_open=True
        )
        existing_response = self.client.post(
            reverse("programme_register", args=[programme_existing.slug]),
            {"full_name": "A B", "email": self.existing.email, "message": "x"},
        )
        new_response = self.client.post(
            reverse("programme_register", args=[programme_new.slug]),
            {"full_name": "A B", "email": "brand-new@example.com", "message": "x"},
        )
        self.assertEqual(existing_response.status_code, 302)
        self.assertEqual(new_response.status_code, 302)
        self.assertFalse(Registration.objects.filter(student=self.existing).exists())
        self.assertTrue(
            Registration.objects.filter(student__email="brand-new@example.com").exists()
        )
        self.assertNotIn("_auth_user_id", self.client.session)
