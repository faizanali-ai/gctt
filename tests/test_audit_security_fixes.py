from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.enquiries.models import Enquiry
from apps.jobs.models import Job
from apps.training.models import Category, Programme


class AuditSecurityFixesTest(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            email="ceo@gctekton.com",
            first_name="Executive",
            last_name="Leader",
            role=User.Role.CEO,
            is_staff=True,
        )
        self.staff_user.set_password("Secret123!")
        self.staff_user.save()

        self.candidate = User.objects.create_user(
            email="existing.candidate@example.com",
            first_name="Existing",
            last_name="Candidate",
            account_type=User.AccountType.CANDIDATE,
        )
        self.candidate.set_password("CandidateSecret123!")
        self.candidate.save()

        self.job = Job.objects.create(
            title="Senior Solutions Architect",
            description="Enterprise architecture role.",
            published=True,
        )

        cat = Category.objects.create(name="Enterprise SAP", published=True)
        self.programme = Programme.objects.create(
            title="SAP S/4HANA Masterclass",
            category=cat,
            description="Deep enterprise curriculum.",
            published=True,
            registration_open=True,
        )

    def test_anonymous_job_apply_cannot_hijack_existing_user(self):
        """Applying with an existing user's email must NOT log in as that user."""
        pdf_content = b"%PDF-1.4 sample content for resume"
        resume = SimpleUploadedFile("resume.pdf", pdf_content, content_type="application/pdf")

        response = self.client.post(
            reverse("job_apply", args=[self.job.slug]),
            data={
                "first_name": "Attacker",
                "last_name": "Impostor",
                "email": "ceo@gctekton.com",
                "phone": "+1 555 123 4567",
                "work_authorization": "us_citizen",
                "message": "Attempting auth bypass",
                "resume": resume,
            },
            follow=False,
        )
        # Must redirect to login, NOT dashboard
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)
        # Session must NOT be authenticated as CEO
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_anonymous_programme_register_cannot_hijack_existing_user(self):
        """Registering for a programme with an existing user's email must NOT log in as that user."""
        response = self.client.post(
            reverse("programme_register", args=[self.programme.slug]),
            data={
                "full_name": "Attacker Impostor",
                "email": "ceo@gctekton.com",
                "phone": "+1 555 123 4567",
                "career_status": "Employed",
                "message": "Attempting training auth bypass",
            },
            follow=False,
        )
        # Must redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)
        # Session must NOT be authenticated as CEO
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_api_career_advisor_accepts_multiple_field_variants(self):
        """API career advisor accepts both current_role/interests and role/target_role."""
        res1 = self.client.post(
            reverse("api_career_advisor"),
            data='{"role": "Financial Analyst", "target_role": "SAP FICO"}',
            content_type="application/json",
        )
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertTrue(data1.get("success"))
        self.assertIn("track", data1["data"])
        self.assertTrue(len(data1["data"]["summary"]) > 0)
        self.assertTrue(len(data1["data"]["guidance"]) > 0)

        # Alias route /api/career-advisor/ also works
        res2 = self.client.post(
            "/api/career-advisor/",
            data='{"current_role": "QA Engineer", "interests": "Cloud Architecture"}',
            content_type="application/json",
        )
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(res2.json().get("success"))

    def test_homepage_enquiry_category_dropdown_saved_correctly(self):
        """Submitting enquiry with category dropdown from home sets category."""
        response = self.client.post(
            reverse("submit_enquiry"),
            data={
                "name": "Enterprise Buyer",
                "email": "buyer@enterprise.com",
                "phone": "+1 469 555 0100",
                "category": "it_staffing",
                "message": "Need 5 senior SAP contractors for Q1 project.",
                "next": reverse("home"),
            },
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        enquiry = Enquiry.objects.filter(email="buyer@enterprise.com").first()
        self.assertIsNotNone(enquiry)
        self.assertEqual(enquiry.category, Enquiry.Category.IT_STAFFING)

    def test_verification_url_uses_configured_site_url(self):
        """Verification URL does not trust arbitrary host headers."""
        from config.emails import verification_url

        with override_settings(SITE_URL="https://gctekton.com"):
            url = verification_url(self.candidate)
            self.assertTrue(url.startswith("https://gctekton.com/accounts/verify/"))
