from django.contrib.auth.models import Group
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.apps import assign_permissions
from apps.accounts.models import User
from apps.jobs.models import Application, Job
from apps.training.models import Programme, Registration

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


def staff_user(email, subgroup):
    user = User.objects.create_user(
        email=email, password="test-pass-12345", role=User.Role.STAFF, is_staff=True
    )
    user.groups.add(Group.objects.get(name=subgroup))
    return user


@override_settings(EMAIL_BACKEND=LOCMEM)
class VisibilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()
        cls.admin = User.objects.create_superuser(
            email="admin@example.com", password="test-pass-12345"
        )
        cls.recruiter = staff_user("recruiter@example.com", "Recruiter")
        cls.trainer = staff_user("trainer@example.com", "Trainer")
        cls.candidate = User.objects.create_user(
            email="candidate@example.com",
            password="test-pass-12345",
            account_type=User.AccountType.CANDIDATE,
        )
        cls.student = User.objects.create_user(
            email="student@example.com",
            password="test-pass-12345",
            account_type=User.AccountType.STUDENT,
        )
        cls.job = Job.objects.create(
            title="Platform Engineer", location="Remote", description="x", published=True
        )
        cls.application = Application.objects.create(
            job=cls.job, applicant=cls.candidate, resume="resumes/x.pdf"
        )
        cls.programme = Programme.objects.create(
            title="SAP Basics", description="x", published=True, registration_open=True
        )
        cls.registration = Registration.objects.create(
            programme=cls.programme, student=cls.student
        )

    def test_admin_sees_account_totals(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard"))
        self.assertIn("accounts_total", response.context["stats"])
        self.assertGreaterEqual(response.context["stats"]["accounts_total"], 4)
        self.assertContains(response, "Accounts:")

    def test_staff_dashboard_has_no_aggregate_stats(self):
        self.client.force_login(self.recruiter)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["stats"], {})
        self.assertNotContains(response, "Accounts:")
        self.assertNotContains(response, "Manage Staff")

    def test_staff_cannot_see_user_directory(self):
        self.client.force_login(self.recruiter)
        self.assertEqual(self.client.get(reverse("manage_users")).status_code, 403)
        other = staff_user("other.recruiter@example.com", "Recruiter")
        response = self.client.get(reverse("dashboard"))
        self.assertNotContains(response, other.email)
        self.assertNotContains(response, "Manage Staff")

    def test_uuid_and_legacy_urls_resolve(self):
        self.assertIn(str(self.application.uuid), reverse("withdraw_application", args=[self.application.uuid]))
        self.assertIn(str(self.application.pk), reverse("withdraw_application_legacy", args=[self.application.pk]))
        self.assertIn(str(self.application.uuid), reverse("staff_application_status", args=[self.application.uuid]))
        self.assertIn(str(self.registration.uuid), reverse("staff_registration_status", args=[self.registration.uuid]))
        self.assertIn(str(self.registration.uuid), reverse("staff_registration_certificate", args=[self.registration.uuid]))

    def test_staff_can_update_application_by_uuid(self):
        self.client.force_login(self.recruiter)
        response = self.client.post(
            reverse("staff_application_status", args=[self.application.uuid]),
            {"status": "shortlisted"},
        )
        self.assertRedirects(response, reverse("staff_applications"))
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.SHORTLISTED)

    def test_candidate_can_withdraw_by_uuid(self):
        self.client.force_login(self.candidate)
        response = self.client.post(
            reverse("withdraw_application", args=[self.application.uuid])
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertFalse(Application.objects.filter(pk=self.application.pk).exists())

    def test_staff_records_do_not_appear_in_operational_lists(self):
        other_staff = staff_user("hidden.staff@example.com", "Trainer")
        Application.objects.create(
            job=self.job, applicant=other_staff, resume="resumes/x.pdf"
        )
        Registration.objects.create(programme=self.programme, student=other_staff)
        self.client.force_login(self.recruiter)
        self.assertNotContains(
            self.client.get(reverse("staff_applications")), other_staff.email
        )
        self.client.force_login(self.trainer)
        self.assertNotContains(
            self.client.get(reverse("staff_registrations")), other_staff.email
        )

    def test_django_admin_is_removed(self):
        self.client.force_login(self.recruiter)
        self.assertEqual(self.client.get("/admin/").status_code, 404)

    def test_admin_sees_user_directory(self):
        other = staff_user("other.recruiter@example.com", "Recruiter")
        self.client.force_login(self.admin)
        response = self.client.get(reverse("manage_users"))
        self.assertContains(response, other.email)
        self.assertContains(response, "Recruiter")

    def test_staff_pagination_hides_totals(self):
        for i in range(30):
            Application.objects.create(
                job=self.job,
                applicant=User.objects.create_user(
                    email=f"c{i}@example.com", password="test-pass-12345"
                ),
                resume="resumes/x.pdf",
            )
        self.client.force_login(self.recruiter)
        response = self.client.get(reverse("staff_applications"))
        self.assertNotContains(response, "Page <span")
        self.client.force_login(self.admin)
        response = self.client.get(reverse("staff_applications"))
        self.assertContains(response, "Page <span")

    def test_student_dashboard_only_has_registrations(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("dashboard"))
        self.assertIn("registrations", response.context)
        self.assertNotIn("applications", response.context)
        self.assertNotContains(response, "GCTT-")
        self.assertNotContains(response, self.candidate.email)

    def test_candidate_dashboard_only_has_applications(self):
        self.client.force_login(self.candidate)
        response = self.client.get(reverse("dashboard"))
        self.assertIn("applications", response.context)
        self.assertNotIn("registrations", response.context)
        self.assertNotContains(response, self.student.email)

    def test_student_cannot_apply_for_job(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse("job_apply", args=[self.job.slug]),
            {
                "resume": SimpleUploadedFile("cv.pdf", b"%PDF-1.4"),
                "message": "x",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Application.objects.filter(applicant=self.student).exists())

    def test_candidate_cannot_register_for_programme(self):
        self.client.force_login(self.candidate)
        response = self.client.post(
            reverse("programme_register", args=[self.programme.slug]),
            {"message": "x"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Registration.objects.filter(student=self.candidate).exists())

    def test_staff_notifications_are_single_recipient(self):
        recruiter_two = staff_user("recruiter2@example.com", "Recruiter")
        job = Job.objects.create(
            title="Second Role", location="Remote", description="x", published=True
        )
        mail.outbox.clear()
        self.client.force_login(self.candidate)
        self.client.post(
            reverse("job_apply", args=[job.slug]),
            {
                "resume": SimpleUploadedFile("cv.pdf", b"%PDF-1.4"),
                "message": "x",
            },
        )
        staff_messages = [
            m
            for m in mail.outbox
            if set(m.to) & {self.recruiter.email, recruiter_two.email}
        ]
        self.assertEqual(len(staff_messages), 2)
        for message in staff_messages:
            self.assertEqual(len(message.to), 1)

    def test_registration_notifications_are_trainer_only_and_single_recipient(self):
        trainer_two = staff_user("trainer2@example.com", "Trainer")
        programme = Programme.objects.create(
            title="Cloud Basics", description="x", published=True, registration_open=True
        )
        mail.outbox.clear()
        self.client.force_login(self.student)
        self.client.post(
            reverse("programme_register", args=[programme.slug]),
            {"message": "x"},
        )
        staff_messages = [
            m
            for m in mail.outbox
            if set(m.to) & {self.trainer.email, trainer_two.email}
        ]
        self.assertEqual(len(staff_messages), 2)
        for message in staff_messages:
            self.assertEqual(len(message.to), 1)
            self.assertNotIn(self.admin.email, message.to)

    def test_trainer_can_download_certificate(self):
        self.registration.issue_certificate()
        self.client.force_login(self.trainer)
        response = self.client.get(
            reverse("download_certificate", args=[self.registration.certificate_ref])
        )
        self.assertEqual(response.status_code, 200)

    def test_recruiter_cannot_download_certificate(self):
        self.registration.issue_certificate()
        self.client.force_login(self.recruiter)
        response = self.client.get(
            reverse("download_certificate", args=[self.registration.certificate_ref])
        )
        self.assertEqual(response.status_code, 404)
