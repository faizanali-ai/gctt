from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.accounts.models import AuditLog, TeamProfile, User
from apps.jobs.models import Application, Job
from apps.training.models import Programme, Registration

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


@override_settings(EMAIL_BACKEND=LOCMEM)
class VerificationTests(TestCase):
    def test_signup_sends_verification_email(self):
        response = self.client.post(
            reverse("signup"),
            {
                "account_type": "candidate",
                "email": "new@example.com",
                "first_name": "New",
                "last_name": "Person",
                "password1": "test-pass-12345",
                "password2": "test-pass-12345",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Verify your GCTT email", mail.outbox[0].subject)

    def test_verification_link_marks_verified(self):
        user = User.objects.create_user(email="v@example.com", password="test-pass-12345")
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        response = self.client.get(reverse("verify_email", args=[uid, token]), follow=True)
        self.assertContains(response, "Email verified")
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

    def test_bad_token_is_rejected(self):
        user = User.objects.create_user(email="b@example.com", password="test-pass-12345")
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        response = self.client.get(
            reverse("verify_email", args=[uid, "bad-token"]), follow=True
        )
        self.assertContains(response, "invalid or has expired")
        user.refresh_from_db()
        self.assertFalse(user.email_verified)


@override_settings(EMAIL_BACKEND=LOCMEM)
class NotificationTests(TestCase):
    def test_enquiry_alerts_staff(self):
        self.client.post(
            reverse("submit_enquiry"),
            {"name": "A", "email": "a@example.com", "category": "general", "message": "Hi"},
        )
        recipients = [message.to[0] for message in mail.outbox]
        self.assertIn("Accounts@gctekton.com", recipients)
        self.assertIn("a@example.com", recipients)

    def test_enquiry_error_preserves_typed_input(self):
        response = self.client.post(
            reverse("submit_enquiry"),
            {
                "name": "A",
                "email": "not-an-email",
                "message": "A long message that must survive validation.",
                "next": "contact",
            },
            follow=True,
        )
        self.assertContains(response, "A long message that must survive validation.")
        self.assertContains(response, "Please check:")

    def test_application_confirms_to_candidate(self):
        user = User.objects.create_user(email="c@example.com", password="test-pass-12345")
        job = Job.objects.create(title="Dev", location="Remote", description="x", published=True)
        self.client.force_login(user)
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.post(
            reverse("job_apply", args=[job.slug]),
            {
                "resume": SimpleUploadedFile("cv.pdf", b"%PDF-1.4"),
                "message": "I'm keen",
            },
        )
        self.assertTrue(Application.objects.exists())
        recipients = [message.to[0] for message in mail.outbox]
        self.assertIn("c@example.com", recipients)
        self.assertIn("Jobs@gctekton.com", recipients)


class CertificateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth.models import Group

        from apps.accounts.apps import assign_permissions

        assign_permissions()
        cls.trainer = User.objects.create_user(
            email="trainer@example.com", password="test-pass-12345", is_staff=True
        )
        cls.trainer.groups.add(Group.objects.get(name="Trainer"))
        cls.student = User.objects.create_user(email="s@example.com", password="test-pass-12345")
        cls.other = User.objects.create_user(email="o@example.com", password="test-pass-12345")
        cls.programme = Programme.objects.create(title="SAP", description="x", published=True)
        cls.registration = Registration.objects.create(
            programme=cls.programme,
            student=cls.student,
            status=Registration.Status.COMPLETED,
        )

    def test_cannot_issue_before_completed(self):
        self.registration.status = Registration.Status.ACCEPTED
        self.registration.save()
        self.client.force_login(self.trainer)
        self.client.post(reverse("staff_registration_certificate", args=[self.registration.pk]))
        self.registration.refresh_from_db()
        self.assertFalse(self.registration.certificate_issued)

    def test_trainer_issues_certificate(self):
        self.client.force_login(self.trainer)
        self.client.post(reverse("staff_registration_certificate", args=[self.registration.pk]))
        self.registration.refresh_from_db()
        self.assertTrue(self.registration.certificate_issued)
        self.assertTrue(self.registration.certificate_ref.startswith("GCTT-"))

    def test_public_verification_page(self):
        self.registration.issue_certificate()
        response = self.client.get(
            reverse("verify_certificate", args=[self.registration.certificate_ref])
        )
        self.assertContains(response, "Valid certificate")
        self.assertContains(response, self.student.display_name)

    def test_unknown_reference_is_not_found(self):
        response = self.client.get(reverse("verify_certificate", args=["GCTT-NOPE"]))
        self.assertContains(response, "Not found")

    def test_owner_can_download_pdf(self):
        self.registration.issue_certificate()
        self.client.force_login(self.student)
        response = self.client.get(
            reverse("download_certificate", args=[self.registration.certificate_ref])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_other_user_cannot_download(self):
        self.registration.issue_certificate()
        self.client.force_login(self.other)
        response = self.client.get(
            reverse("download_certificate", args=[self.registration.certificate_ref])
        )
        self.assertEqual(response.status_code, 403)


class DraftPreviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth.models import Group

        from apps.accounts.apps import assign_permissions

        assign_permissions()
        cls.staff = User.objects.create_user(
            email="r@example.com", password="test-pass-12345", is_staff=True
        )
        cls.staff.groups.add(Group.objects.get(name="Recruiter"))
        cls.job = Job.objects.create(title="Hidden", location="x", description="x")

    def test_public_cannot_see_draft(self):
        self.assertEqual(self.client.get(reverse("job_detail", args=[self.job.slug])).status_code, 404)

    def test_recruiter_can_preview_draft(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("job_detail", args=[self.job.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Draft preview")


class ListPaginationTests(TestCase):
    def test_job_list_paginates(self):
        for i in range(12):
            Job.objects.create(title=f"Job {i}", location="Remote", description="x", published=True)
        response = self.client.get(reverse("careers"))
        self.assertEqual(len(response.context["page_obj"]), 10)
        response = self.client.get(reverse("careers"), {"page": 2})
        self.assertEqual(len(response.context["page_obj"]), 2)

    def test_job_list_type_filter(self):
        Job.objects.create(title="A", location="x", description="x", published=True, employment_type="contract")
        Job.objects.create(title="B", location="x", description="x", published=True, employment_type="full_time")
        response = self.client.get(reverse("careers"), {"type": "contract"})
        self.assertEqual(len(response.context["page_obj"]), 1)


class TeamProfileTests(TestCase):
    def test_published_profiles_appear_on_about(self):
        TeamProfile.objects.create(name="Visible Person", published=True)
        TeamProfile.objects.create(name="Hidden Person", published=False)
        response = self.client.get(reverse("about"))
        self.assertContains(response, "Visible Person")
        self.assertNotContains(response, "Hidden Person")


class EnquiryCategoryTests(TestCase):
    def test_category_and_details_inferred_from_page(self):
        from apps.enquiries.models import Enquiry

        self.client.post(
            reverse("submit_enquiry"),
            {
                "name": "Acme HR",
                "email": "hr@acme.com",
                "company": "Acme",
                "area": "SAP",
                "how_heard": "LinkedIn",
                "message": "We need two SAP consultants.",
                "next": "employers",
            },
        )
        enquiry = Enquiry.objects.get()
        self.assertEqual(enquiry.category, Enquiry.Category.EMPLOYER_INTAKE)
        self.assertEqual(enquiry.company, "Acme")
        self.assertEqual(enquiry.area, "SAP")
        self.assertEqual(enquiry.how_heard, "LinkedIn")


class ApplicationRuleTests(TestCase):
    def test_message_is_required(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        user = User.objects.create_user(email="a@example.com", password="test-pass-12345")
        job = Job.objects.create(title="Dev", location="x", description="x", published=True)
        self.client.force_login(user)
        self.client.post(
            reverse("job_apply", args=[job.slug]),
            {"resume": SimpleUploadedFile("cv.pdf", b"%PDF-1.4")},
        )
        self.assertFalse(Application.objects.exists())
        self.client.post(
            reverse("job_apply", args=[job.slug]),
            {"resume": SimpleUploadedFile("cv.pdf", b"%PDF-1.4"), "message": "Keen"},
        )
        self.assertTrue(Application.objects.exists())

    def test_candidate_can_withdraw_own_application(self):
        user = User.objects.create_user(email="w@example.com", password="test-pass-12345")
        job = Job.objects.create(title="Dev", location="x", description="x", published=True)
        application = Application.objects.create(job=job, applicant=user, resume="resumes/x.pdf")
        self.client.force_login(user)
        response = self.client.post(reverse("withdraw_application", args=[application.pk]))
        self.assertRedirects(response, reverse("dashboard"))
        self.assertFalse(Application.objects.exists())
        audit = AuditLog.objects.get(action="application.withdraw")
        self.assertEqual(audit.actor, user)
        self.assertEqual(audit.details, "Dev")

    def test_cannot_withdraw_someone_elses_application(self):
        owner = User.objects.create_user(email="o@example.com", password="test-pass-12345")
        other = User.objects.create_user(email="x@example.com", password="test-pass-12345")
        job = Job.objects.create(title="Dev", location="x", description="x", published=True)
        application = Application.objects.create(job=job, applicant=owner, resume="resumes/x.pdf")
        self.client.force_login(other)
        response = self.client.post(reverse("withdraw_application", args=[application.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Application.objects.exists())


class SeoTests(TestCase):
    def test_sitemap_lists_static_and_job_urls(self):
        job = Job.objects.create(title="Seo Job", location="x", description="x", published=True)
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/careers/")
        self.assertContains(response, f"/careers/{job.slug}/")

    def test_robots_points_to_sitemap(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sitemap:")

    def test_home_has_structured_data_and_og_image(self):
        response = self.client.get("/")
        self.assertContains(response, '"@type": "Organization"')
        self.assertContains(response, "og-gctt-v2.jpg")
        self.assertContains(response, 'rel="canonical"')
