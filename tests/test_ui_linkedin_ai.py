from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.apps import assign_permissions
from apps.accounts.models import User
from apps.jobs.models import Application, Job


class UIUXLinkedInAITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()
        cls.recruiter = User.objects.create_user(
            email="recruiter.test@gctekton.com",
            password="test-pass-12345",
            is_staff=True,
            role=User.Role.STAFF,
        )
        cls.job = Job.objects.create(
            title="Senior SAP S/4HANA Architect",
            location="Irving, TX (Hybrid)",
            description="Lead cross-functional enterprise ERP transformation.",
            requirements="10+ years SAP implementation, S/4HANA migration experience.",
            published=True,
        )

    def test_brand_and_primary_nav_rendered_on_home(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("logo-horizontal", content)
        self.assertIn('aria-label="GCTT home"', content)
        self.assertIn("Talent Solutions", content)
        self.assertIn("Academy", content)
        self.assertIn("Careers", content)
        self.assertIn("Company", content)
        self.assertIn("Contact", content)
        self.assertIn("Request talent", content)
        self.assertIn("Portal sign in", content)

    def test_ai_career_advisor_api_returns_structured_roadmap(self):
        response = self.client.post(
            reverse("api_career_advisor"),
            data='{"current_role": "Senior Financial Accountant", "experience": "5", "interests": "high_paying_erp"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertIn("SAP S/4HANA", data["data"]["track"])
        self.assertGreaterEqual(data["data"]["fit_score"], 90)
        self.assertIn("milestones", data["data"])

    def test_unauthenticated_candidate_can_apply_directly_from_linkedin(self):
        # Fake valid PDF file (starts with %PDF)
        pdf_content = b"%PDF-1.4 sample content for resume"
        resume = SimpleUploadedFile("jane_resume.pdf", pdf_content, content_type="application/pdf")

        response = self.client.post(
            reverse("job_apply", args=[self.job.slug]),
            data={
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane.doe.candidate@example.com",
                "phone": "+1 (555) 234-5678",
                "work_authorization": "us_citizen",
                "message": "Senior architect with 8 years enterprise experience.",
                "resume": resume,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("job_detail", args=[self.job.slug]))
        self.assertNotIn("_auth_user_id", self.client.session)

        # Verify candidate account was auto-provisioned
        candidate = User.objects.get(email="jane.doe.candidate@example.com")
        self.assertEqual(candidate.first_name, "Jane")
        self.assertEqual(candidate.last_name, "Doe")
        self.assertEqual(candidate.phone, "+1 (555) 234-5678")

        # Verify application was recorded
        app = Application.objects.get(job=self.job, applicant=candidate)
        self.assertEqual(app.status, Application.Status.SUBMITTED)
        self.assertIn("[Work Auth:", app.message)

    def test_staff_linkedin_posting_endpoint(self):
        self.client.force_login(self.recruiter)
        # Give permission
        from django.contrib.auth.models import Permission
        p = Permission.objects.get(codename="change_job")
        self.recruiter.user_permissions.add(p)

        response = self.client.post(reverse("staff_job_linkedin_post", args=[self.job.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("staff_jobs"))
