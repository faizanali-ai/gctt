from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.apps import assign_permissions
from apps.accounts.models import User
from apps.jobs.models import Application, Job
from apps.training.models import Category, Programme, Registration


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CandidatePrivacyAndDataIsolationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()

        # Create two distinct candidates
        cls.candidate_a = User.objects.create_user(
            email="candidate.a@example.com",
            password="test-password-123",
            first_name="Candidate",
            last_name="Alpha",
            account_type=User.AccountType.CANDIDATE,
            is_staff=False,
        )
        cls.candidate_b = User.objects.create_user(
            email="candidate.b@example.com",
            password="test-password-123",
            first_name="Candidate",
            last_name="Beta",
            account_type=User.AccountType.CANDIDATE,
            is_staff=False,
        )

        # Create a Job
        cls.job = Job.objects.create(
            title="Senior Systems Architect",
            slug="senior-systems-architect",
            location="Irving, TX",
            employment_type=Job.EmploymentType.FULL_TIME,
            description="Enterprise architecture role.",
            published=True,
        )

        # Applications
        cls.app_a = Application.objects.create(
            job=cls.job,
            applicant=cls.candidate_a,
            status=Application.Status.SUBMITTED,
        )
        cls.app_b = Application.objects.create(
            job=cls.job,
            applicant=cls.candidate_b,
            status=Application.Status.SUBMITTED,
        )

        # Programme & Registrations
        cls.category = Category.objects.create(name="SAP", published=True)
        cls.programme = Programme.objects.create(
            title="SAP S/4HANA Finance",
            slug="sap-s4hana-finance",
            category=cls.category,
            description="Core financial accounting.",
            published=True,
        )
        cls.reg_a = Registration.objects.create(
            programme=cls.programme,
            student=cls.candidate_a,
            status=Registration.Status.ACCEPTED,
            certificate_ref="GCTT-AAAA1111",
            certificate_issued=True,
        )
        cls.reg_b = Registration.objects.create(
            programme=cls.programme,
            student=cls.candidate_b,
            status=Registration.Status.ACCEPTED,
            certificate_ref="GCTT-BBBB2222",
            certificate_issued=True,
        )

    def test_candidate_a_cannot_see_candidate_b_on_dashboard(self):
        """Candidate A's dashboard must only list Candidate A's own applications and registrations."""
        self.client.force_login(self.candidate_a)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

        # Context isolation
        applications = response.context["applications"]
        registrations = response.context["registrations"]

        self.assertIn(self.app_a, applications)
        self.assertNotIn(self.app_b, applications)

        self.assertIn(self.reg_a, registrations)
        self.assertNotIn(self.reg_b, registrations)

        # HTML isolation
        self.assertNotContains(response, self.candidate_b.email)
        self.assertNotContains(response, "GCTT-BBBB2222")

    def test_candidate_a_cannot_withdraw_candidate_b_application(self):
        """Candidate A attempting to withdraw Candidate B's application must return 404."""
        self.client.force_login(self.candidate_a)
        response = self.client.post(reverse("withdraw_application", args=[self.app_b.pk]))
        self.assertEqual(response.status_code, 404)
        # Verify app_b still exists
        self.assertTrue(Application.objects.filter(pk=self.app_b.pk).exists())

    def test_candidate_a_cannot_download_candidate_b_certificate(self):
        """Candidate A attempting to download Candidate B's certificate PDF must receive 403 Forbidden."""
        self.client.force_login(self.candidate_a)
        response = self.client.get(reverse("download_certificate", args=[self.reg_b.certificate_ref]))
        self.assertEqual(response.status_code, 403)

    def test_candidate_cannot_access_staff_application_list(self):
        """Non-staff candidate attempting to access /staff/applications/ must receive 403."""
        self.client.force_login(self.candidate_a)
        response = self.client.get(reverse("staff_applications"))
        self.assertEqual(response.status_code, 403)

    def test_candidate_cannot_access_staff_registrations_list(self):
        """Non-staff candidate attempting to access /staff/registrations/ must receive 403."""
        self.client.force_login(self.candidate_a)
        response = self.client.get(reverse("staff_registrations"))
        self.assertEqual(response.status_code, 403)

    def test_candidate_cannot_access_user_management(self):
        """Non-staff candidate attempting to access /manage/users/ must receive 403."""
        self.client.force_login(self.candidate_a)
        response = self.client.get(reverse("manage_users"))
        self.assertEqual(response.status_code, 403)

    def test_candidate_cannot_access_enquiries_list(self):
        """Non-staff candidate attempting to access /staff/enquiries/ must receive 403."""
        self.client.force_login(self.candidate_a)
        response = self.client.get(reverse("staff_enquiries"))
        self.assertEqual(response.status_code, 403)
