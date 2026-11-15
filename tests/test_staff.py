from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.accounts.apps import assign_permissions
from apps.accounts.models import User
from apps.enquiries.models import Enquiry
from apps.jobs.models import Application, Job
from apps.training.models import Programme, Registration


def make_employee(email, group_name):
    user = User.objects.create_user(
        email=email, password="test-pass-12345", is_staff=True, first_name=group_name
    )
    user.groups.add(Group.objects.get(name=group_name))
    return user


class StaffPortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()  # groups + permissions, in case post_migrate didn't run
        cls.recruiter = make_employee("recruiter@gcttekton.com", "Recruiter")
        cls.trainer = make_employee("trainer@gcttekton.com", "Trainer")
        cls.enquiry_manager = make_employee("enquiries@gcttekton.com", "Enquiry Manager")
        cls.ceo = User.objects.create_superuser(email="ceo@gcttekton.com", password="test-pass-12345")
        cls.candidate = User.objects.create_user(
            email="candidate@example.com", password="test-pass-12345"
        )
        cls.job = Job.objects.create(
            title="Platform Engineer", location="Remote", description="x", published=False
        )
        cls.application = Application.objects.create(
            job=cls.job, applicant=cls.candidate, resume="resumes/x.pdf"
        )
        cls.programme = Programme.objects.create(
            title="SAP Basics", description="x", published=False, registration_open=False
        )
        cls.registration = Registration.objects.create(
            programme=cls.programme, student=cls.candidate
        )
        cls.enquiry = Enquiry.objects.create(
            name="Visitor", email="v@example.com", message="Hello"
        )

    def test_recruiter_sees_jobs_and_applications_only(self):
        self.client.force_login(self.recruiter)
        self.assertEqual(self.client.get(reverse("staff_jobs")).status_code, 200)
        self.assertEqual(self.client.get(reverse("staff_applications")).status_code, 200)
        self.assertEqual(self.client.get(reverse("staff_enquiries")).status_code, 403)
        self.assertEqual(self.client.get(reverse("staff_programmes")).status_code, 403)

    def test_trainer_sees_training_only(self):
        self.client.force_login(self.trainer)
        self.assertEqual(self.client.get(reverse("staff_programmes")).status_code, 200)
        self.assertEqual(self.client.get(reverse("staff_registrations")).status_code, 200)
        self.assertEqual(self.client.get(reverse("staff_jobs")).status_code, 403)

    def test_enquiry_manager_sees_enquiries_only(self):
        self.client.force_login(self.enquiry_manager)
        self.assertEqual(self.client.get(reverse("staff_enquiries")).status_code, 200)
        self.assertEqual(self.client.get(reverse("staff_applications")).status_code, 403)

    def test_ceo_sees_everything(self):
        self.client.force_login(self.ceo)
        for name in ("staff_enquiries", "staff_jobs", "staff_applications",
                     "staff_programmes", "staff_registrations"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_candidate_is_blocked(self):
        self.client.force_login(self.candidate)
        self.assertEqual(self.client.get(reverse("staff_jobs")).status_code, 403)

    def test_recruiter_moves_application_forward(self):
        self.client.force_login(self.recruiter)
        self.client.post(
            reverse("staff_application_status", args=[self.application.pk]),
            {"status": "shortlisted"},
        )
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.SHORTLISTED)

    def test_recruiter_publishes_job(self):
        self.client.force_login(self.recruiter)
        self.client.post(reverse("staff_job_publish", args=[self.job.pk]))
        self.job.refresh_from_db()
        self.assertTrue(self.job.published)

    def test_trainer_opens_registration(self):
        self.client.force_login(self.trainer)
        self.client.post(
            reverse("staff_programme_toggle", args=[self.programme.pk]),
            {"field": "registration_open"},
        )
        self.programme.refresh_from_db()
        self.assertTrue(self.programme.registration_open)

    def test_enquiry_manager_updates_status(self):
        self.client.force_login(self.enquiry_manager)
        self.client.post(
            reverse("staff_enquiry_status", args=[self.enquiry.pk]), {"status": "resolved"}
        )
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.status, Enquiry.Status.RESOLVED)

    def test_staff_dashboard_shows_only_own_sections(self):
        self.client.force_login(self.recruiter)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Applications")
        self.assertNotContains(response, "Enquiries")

    def test_public_signup_cannot_create_employer(self):
        response = self.client.post(
            reverse("signup"),
            {
                "account_type": "employer",
                "email": "e@example.com",
                "first_name": "E",
                "last_name": "X",
                "password1": "test-pass-12345",
                "password2": "test-pass-12345",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="e@example.com").exists())
