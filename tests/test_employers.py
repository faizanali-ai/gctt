from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.jobs.models import Application, Job


class EmployerPortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.employer = User.objects.create_user(
            email="hr@acme.com",
            password="test-pass-12345",
            account_type=User.AccountType.EMPLOYER,
            company_name="Acme",
        )
        cls.other_employer = User.objects.create_user(
            email="hr@other.com",
            password="test-pass-12345",
            account_type=User.AccountType.EMPLOYER,
            company_name="Other Co",
        )
        cls.candidate = User.objects.create_user(
            email="candidate@example.com", password="test-pass-12345"
        )
        cls.staff = User.objects.create_user(
            email="ceo@gcttekton.com", password="test-pass-12345", is_staff=True
        )
        cls.job = Job.objects.create(
            title="Acme Developer",
            location="Remote",
            description="Build things",
            employer=cls.employer,
            published=True,
        )
        cls.application = Application.objects.create(
            job=cls.job, applicant=cls.candidate, resume="resumes/x.pdf"
        )

    def test_employer_dashboard_lists_own_jobs(self):
        self.client.force_login(self.employer)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Acme Developer")

    def test_employer_cannot_touch_another_employers_job(self):
        self.client.force_login(self.other_employer)
        response = self.client.get(reverse("employer_job_edit", args=[self.job.slug]))
        self.assertEqual(response.status_code, 404)
        response = self.client.post(
            reverse("employer_application_status", args=[self.application.pk]),
            {"status": "shortlisted"},
        )
        self.assertEqual(response.status_code, 404)

    def test_employer_creates_draft_job(self):
        self.client.force_login(self.employer)
        response = self.client.post(
            reverse("employer_job_new"),
            {
                "title": "New Role",
                "location": "Irving, TX",
                "employment_type": "full_time",
                "description": "Do the work",
                "requirements": "",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        job = Job.objects.get(title="New Role")
        self.assertEqual(job.employer, self.employer)
        self.assertFalse(job.published)

    def test_employer_can_advance_own_application(self):
        self.client.force_login(self.employer)
        self.client.post(
            reverse("employer_application_status", args=[self.application.pk]),
            {"status": "shortlisted"},
        )
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.SHORTLISTED)

    def test_employer_cannot_set_arbitrary_status(self):
        self.client.force_login(self.employer)
        self.client.post(
            reverse("employer_application_status", args=[self.application.pk]),
            {"status": "bogus"},
        )
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.SUBMITTED)

    def test_candidate_is_blocked_from_employer_area(self):
        self.client.force_login(self.candidate)
        self.assertEqual(self.client.get(reverse("employer_job_new")).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_staff_sees_admin_dashboard(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Open Django Admin")

    def test_signup_captures_account_type(self):
        response = self.client.post(
            reverse("signup"),
            {
                "account_type": "employer",
                "company_name": "Hiring Co",
                "email": "new@hiring.co",
                "first_name": "Sam",
                "last_name": "Hiring",
                "password1": "test-pass-12345",
                "password2": "test-pass-12345",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        user = User.objects.get(email="new@hiring.co")
        self.assertTrue(user.is_employer)
        self.assertEqual(user.company_name, "Hiring Co")

    def test_employer_signup_requires_company(self):
        response = self.client.post(
            reverse("signup"),
            {
                "account_type": "employer",
                "company_name": "",
                "email": "nocompany@example.com",
                "first_name": "No",
                "last_name": "Company",
                "password1": "test-pass-12345",
                "password2": "test-pass-12345",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="nocompany@example.com").exists())
