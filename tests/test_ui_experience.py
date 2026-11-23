from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import SiteSettings, User
from apps.jobs.forms import ApplicationForm
from apps.jobs.models import Application, Job
from apps.training.models import Category, Programme, Registration
from config.site import clear_company_cache


class MobileQuickApplyExperienceTests(TestCase):
    def setUp(self):
        clear_company_cache()
        self.candidate = User.objects.create_user(
            email="candidate.experience@example.com",
            password="test-pass-12345",
            account_type=User.AccountType.CANDIDATE,
        )
        self.job = Job.objects.create(
            title="Senior Platform Reliability Engineer",
            location="Irving, TX (Hybrid)",
            description="Leading resilient infrastructure and platform engineering.",
            requirements="Kubernetes, Python, Terraform, CI/CD pipelines.",
            published=True,
        )

    def tearDown(self):
        clear_company_cache()

    def test_job_detail_renders_floating_apply_bar_for_unapplied_visitors(self):
        response = self.client.get(reverse("job_detail", args=[self.job.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-floating-apply")
        self.assertContains(response, "data-apply-hero-cta")
        self.assertContains(response, "Apply Now")
        self.assertContains(response, self.job.title)

    def test_job_detail_hides_floating_apply_bar_when_applications_paused(self):
        settings = SiteSettings.load()
        settings.allow_candidate_applications = False
        settings.save()
        clear_company_cache()

        response = self.client.get(reverse("job_detail", args=[self.job.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "data-floating-apply")

    def test_job_detail_hides_floating_apply_bar_when_candidate_applied(self):
        Application.objects.create(job=self.job, applicant=self.candidate)
        self.client.force_login(self.candidate)

        response = self.client.get(reverse("job_detail", args=[self.job.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "data-floating-apply")
        self.assertContains(response, "You have already applied for this role.")


class ResumeClientValidationTests(TestCase):
    def test_resume_input_has_pdf_accept_and_size_attribute(self):
        form = ApplicationForm()
        resume_widget = form.fields["resume"].widget
        self.assertEqual(resume_widget.attrs.get("accept"), ".pdf,application/pdf")
        self.assertEqual(resume_widget.attrs.get("data-max-size"), "5242880")
        self.assertIn("5 MB", form.fields["resume"].help_text)


class CertificateVerificationResilienceTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            email="student.verify@example.com",
            password="test-pass-12345",
            account_type=User.AccountType.STUDENT,
        )
        self.category = Category.objects.create(name="Enterprise Cloud", published=True)
        self.programme = Programme.objects.create(
            title="SAP S/4HANA Finance Lead",
            category=self.category,
            published=True,
            registration_open=True,
        )
        self.registration = Registration.objects.create(
            programme=self.programme,
            student=self.student,
            status=Registration.Status.COMPLETED,
        )
        self.registration.issue_certificate()
        self.ref = self.registration.certificate_ref

    def test_verify_certificate_accepts_code_query_param(self):
        response = self.client.get(reverse("verify_certificate_form") + f"?code={self.ref}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Valid certificate")
        self.assertContains(response, "Verified record")
        self.assertContains(response, self.ref)

    def test_verify_certificate_accepts_certificate_id_query_param(self):
        response = self.client.get(reverse("verify_certificate_form") + f"?certificate_id={self.ref}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Valid certificate")
        self.assertContains(response, self.ref)

    def test_verify_certificate_accepts_q_query_param(self):
        response = self.client.get(reverse("verify_certificate_form") + f"?q={self.ref}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Valid certificate")
        self.assertContains(response, self.ref)

    def test_verify_certificate_normalizes_pasted_url(self):
        pasted_url = f"https://gctekton.com/training/verify/{self.ref}/?next=/training/verify/OTHER/"
        response = self.client.get(reverse("verify_certificate_form") + f"?ref={pasted_url}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Valid certificate")
        self.assertContains(response, self.ref)

    def test_verify_certificate_normalizes_pasted_query_url(self):
        pasted_url = f"https://gctekton.com/training/verify/?ref={self.ref}"
        response = self.client.get(reverse("verify_certificate_form") + f"?ref={pasted_url}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Valid certificate")
        self.assertContains(response, self.ref)

    def test_verify_certificate_is_case_insensitive(self):
        lowercase_ref = self.ref.lower()
        response = self.client.get(reverse("verify_certificate_form") + f"?ref={lowercase_ref}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Valid certificate")
        self.assertContains(response, self.ref)

    def test_verify_certificate_empty_ref_does_not_render_not_found(self):
        from unittest.mock import patch

        with patch("apps.training.views.Registration.objects.select_related") as mock_select_related:
            response = self.client.get(reverse("verify_certificate_form"))
            mock_select_related.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Not found")
        self.assertContains(response, "Enter a certificate reference")

    def test_verify_certificate_unknown_ref_renders_not_found(self):
        response = self.client.get(reverse("verify_certificate_form") + "?ref=GCTT-DOES-NOT-EXIST")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Not found")
        self.assertContains(response, "GCTT-DOES-NOT-EXIST")

    def test_verify_certificate_malformed_url_does_not_error(self):
        malformed = "https://[/training/verify/GCTT-1A2B3C4D/"
        response = self.client.get(reverse("verify_certificate_form") + f"?ref={malformed}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Not found")
