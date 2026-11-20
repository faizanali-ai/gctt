import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group
from django.core import mail
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.admin import AuditLogAdmin
from apps.accounts.apps import assign_permissions
from apps.accounts.models import AuditLog, User
from apps.enquiries.models import Enquiry
from apps.jobs.forms import ApplicationForm
from apps.jobs.models import Application, Job
from apps.training.models import Category, Programme, Registration

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


class CspAndSecurityHeadersTests(TestCase):
    def test_csp_headers_contain_google_fonts(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        csp = response.headers.get("Content-Security-Policy", "")
        self.assertIn("https://fonts.googleapis.com", csp)
        self.assertIn("https://fonts.gstatic.com", csp)

class ResumeUploadAndCleanupTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.user = User.objects.create_user(email="applicant@example.com", password="test-pass-12345")
        self.job = Job.objects.create(title="DevOps", location="Remote", description="x", published=True)

    def test_clean_resume_rejects_unlisted_and_disguised_extensions(self):
        # Empty extension
        form = ApplicationForm(
            data={"message": "Hire me"},
            files={"resume": SimpleUploadedFile("resume", b"#!/bin/sh\nrm -rf /")},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("resume", form.errors)

        # Disguised / arbitrary unlisted extension
        form2 = ApplicationForm(
            data={"message": "Hire me"},
            files={"resume": SimpleUploadedFile("payload.sh", b"echo hacked")},
        )
        self.assertFalse(form2.is_valid())
        self.assertIn("resume", form2.errors)

    def test_application_post_delete_removes_file_from_storage(self):
        application = Application.objects.create(
            job=self.job,
            applicant=self.user,
            resume=SimpleUploadedFile("cv.pdf", b"%PDF-1.4 test content"),
            message="Hello",
        )
        file_path = application.resume.name
        self.assertTrue(default_storage.exists(file_path))

        application.delete()
        self.assertFalse(default_storage.exists(file_path))

    def test_withdraw_application_removes_file_from_storage(self):
        application = Application.objects.create(
            job=self.job,
            applicant=self.user,
            resume=SimpleUploadedFile("cv.pdf", b"%PDF-1.4 test content"),
            message="Hello",
        )
        file_path = application.resume.name
        self.assertTrue(default_storage.exists(file_path))

        self.client.force_login(self.user)
        response = self.client.post(reverse("withdraw_application", args=[application.uuid]))
        self.assertRedirects(response, reverse("dashboard"))
        self.assertFalse(default_storage.exists(file_path))


class CertificateBugTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()
        cls.trainer = User.objects.create_user(
            email="trainer@example.com", password="test-pass-12345", is_staff=True
        )
        cls.trainer.groups.add(Group.objects.get(name="Trainer"))
        cls.student = User.objects.create_user(
            email="student@example.com",
            password="test-pass-12345",
            account_type=User.AccountType.STUDENT,
        )
        cls.programme = Programme.objects.create(title="SAP MM", description="x", published=True)
        cls.registration = Registration.objects.create(
            programme=cls.programme,
            student=cls.student,
            status=Registration.Status.COMPLETED,
        )

    def test_download_certificate_filename_header_format(self):
        self.registration.issue_certificate()
        ref = self.registration.certificate_ref
        self.client.force_login(self.student)
        response = self.client.get(reverse("download_certificate", args=[ref]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Disposition"], f'attachment; filename="{ref}.pdf"')
        self.assertNotIn("GCTT-GCTT-", response["Content-Disposition"])

    def test_revocation_audit_log_preserves_reference(self):
        self.registration.issue_certificate()
        ref = self.registration.certificate_ref
        self.assertTrue(ref.startswith("GCTT-"))

        self.client.force_login(self.trainer)
        response = self.client.post(
            reverse("staff_registration_certificate", args=[self.registration.uuid]),
            {"action": "revoke"},
        )
        self.assertEqual(response.status_code, 302)
        self.registration.refresh_from_db()
        self.assertFalse(self.registration.certificate_issued)
        self.assertIsNone(self.registration.certificate_ref)

        audit = AuditLog.objects.get(action="certificate.revoke")
        self.assertEqual(audit.target, ref)


class StatusChangeDeduplicationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()
        cls.recruiter = User.objects.create_user(
            email="recruiter@example.com", password="test-pass-12345", is_staff=True
        )
        cls.recruiter.groups.add(Group.objects.get(name="Recruiter"))
        cls.trainer = User.objects.create_user(
            email="trainer2@example.com", password="test-pass-12345", is_staff=True
        )
        cls.trainer.groups.add(Group.objects.get(name="Trainer"))
        cls.enquiry_manager = User.objects.create_user(
            email="em@example.com", password="test-pass-12345", is_staff=True
        )
        cls.enquiry_manager.groups.add(Group.objects.get(name="Enquiry Manager"))
        cls.candidate = User.objects.create_user(email="cand@example.com", password="test-pass-12345")
        cls.job = Job.objects.create(title="Engineer", location="Remote", description="x", published=True)
        cls.application = Application.objects.create(
            job=cls.job, applicant=cls.candidate, status=Application.Status.SUBMITTED
        )
        cls.programme = Programme.objects.create(title="Scrum Master", description="x", published=True)
        cls.registration = Registration.objects.create(
            programme=cls.programme, student=cls.candidate, status=Registration.Status.UNDER_REVIEW
        )
        cls.enquiry = Enquiry.objects.create(
            name="John", email="john@example.com", message="Hi", status=Enquiry.Status.NEW
        )

    @override_settings(EMAIL_BACKEND=LOCMEM)
    def test_application_status_duplicate_ignored(self):
        self.client.force_login(self.recruiter)
        # First transition: submitted -> shortlisted
        self.client.post(
            reverse("staff_application_status", args=[self.application.uuid]),
            {"status": Application.Status.SHORTLISTED},
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(AuditLog.objects.filter(action="application.status").count(), 1)

        # Duplicate post with same status
        self.client.post(
            reverse("staff_application_status", args=[self.application.uuid]),
            {"status": Application.Status.SHORTLISTED},
        )
        # Should NOT send second email or log duplicate audit
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(AuditLog.objects.filter(action="application.status").count(), 1)

    @override_settings(EMAIL_BACKEND=LOCMEM)
    def test_registration_status_duplicate_ignored(self):
        self.client.force_login(self.trainer)
        # First transition: under_review -> accepted
        self.client.post(
            reverse("staff_registration_status", args=[self.registration.uuid]),
            {"status": Registration.Status.ACCEPTED},
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(AuditLog.objects.filter(action="registration.status").count(), 1)

        # Duplicate post with same status
        self.client.post(
            reverse("staff_registration_status", args=[self.registration.uuid]),
            {"status": Registration.Status.ACCEPTED},
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(AuditLog.objects.filter(action="registration.status").count(), 1)

    def test_enquiry_status_duplicate_ignored(self):
        self.client.force_login(self.enquiry_manager)
        # First transition: new -> in_progress
        self.client.post(
            reverse("staff_enquiry_status", args=[self.enquiry.pk]),
            {"status": Enquiry.Status.IN_PROGRESS},
        )
        self.assertEqual(AuditLog.objects.filter(action="enquiry.status").count(), 1)

        # Duplicate post with same status
        self.client.post(
            reverse("staff_enquiry_status", args=[self.enquiry.pk]),
            {"status": Enquiry.Status.IN_PROGRESS},
        )
        self.assertEqual(AuditLog.objects.filter(action="enquiry.status").count(), 1)


@override_settings(EMAIL_BACKEND=LOCMEM)
class EnquiryAndSearchBugTests(TestCase):
    def test_enquiry_email_contains_area_and_how_heard(self):
        assign_permissions()
        staff = User.objects.create_user(
            email="enquiries@example.com", password="test-pass-12345", is_staff=True
        )
        staff.groups.add(Group.objects.get(name="Enquiry Manager"))
        self.client.post(
            reverse("submit_enquiry"),
            {
                "name": "Jane",
                "email": "jane@example.com",
                "company": "Tech Corp",
                "area": "SAP",
                "how_heard": "LinkedIn",
                "message": "Interested in SAP training.",
                "next": "training",
            },
        )
        staff_email = next(m for m in mail.outbox if "enquiries@example.com" in m.to)
        self.assertIn("Area: SAP", staff_email.body)
        self.assertIn("How heard: LinkedIn", staff_email.body)

    def test_sap_scrum_enquiry_category(self):
        self.client.post(
            reverse("submit_enquiry"),
            {
                "name": "Bob",
                "email": "bob@example.com",
                "message": "Agile coaching request",
                "next": "sap_scrum",
            },
        )
        enquiry = Enquiry.objects.get(email="bob@example.com")
        self.assertEqual(enquiry.category, Enquiry.Category.TRAINING)

    def test_job_search_matches_requirements(self):
        Job.objects.create(
            title="Backend Engineer",
            location="Irving, TX",
            description="General software development",
            requirements="Expertise with Django and Postgres",
            published=True,
        )
        response = self.client.get(reverse("careers"), {"q": "Postgres"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), 1)
        self.assertEqual(response.context["page_obj"][0].title, "Backend Engineer")


class UserManagementAndAuthBugTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()
        cls.owner = User.objects.create_user(
            email="owner@example.com", password="test-pass-12345", role=User.Role.ADMIN, is_staff=True, is_superuser=True
        )
        cls.superadmin = User.objects.create_user(
            email="superadmin@example.com", password="test-pass-12345", role=User.Role.ADMIN, is_staff=True
        )
        cls.user = User.objects.create_user(
            email="regular@example.com", password="test-pass-12345"
        )

    def test_authenticated_user_redirected_from_login_and_signup(self):
        self.client.force_login(self.user)
        login_res = self.client.get(reverse("login"))
        self.assertRedirects(login_res, reverse("dashboard"))

        signup_res = self.client.get(reverse("signup"))
        self.assertRedirects(signup_res, reverse("dashboard"))

    def test_verify_email_already_verified(self):
        self.user.email_verified = True
        self.user.save()
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.get(reverse("verify_email", args=[uid, "any-token"]), follow=True)
        self.assertContains(response, "Your email is already verified.")

    def test_user_create_and_edit_logged_in_audit_log(self):
        self.client.force_login(self.owner)
        self.client.post(
            reverse("manage_user_create"),
            {
                "email": "newstaff@example.com",
                "first_name": "Test",
                "last_name": "Staff",
                "role": User.Role.STAFF,
                "group": "Recruiter",
                "password": "valid-pass-12345",
            },
        )
        self.assertTrue(AuditLog.objects.filter(action="user.create", target="newstaff@example.com").exists())

        new_user = User.objects.get(email="newstaff@example.com")
        self.client.post(
            reverse("manage_user_edit", args=[new_user.pk]),
            {
                "first_name": "Updated",
                "last_name": "Staff",
                "role": User.Role.STAFF,
                "group": "Recruiter",
                "is_active": "on",
            },
        )
        self.assertTrue(AuditLog.objects.filter(action="user.edit", target="newstaff@example.com").exists())

    def test_audit_log_admin_has_no_delete_permission(self):
        admin_instance = AuditLogAdmin(AuditLog, None)
        self.assertFalse(admin_instance.has_delete_permission(None))

    def test_robots_txt_disallows_manage(self):
        response = self.client.get(reverse("robots"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Disallow: /manage/", response.content.decode())

    def test_programme_sitemap_excludes_unpublished_category(self):
        cat_pub = Category.objects.create(name="Public Cat", published=True)
        cat_unpub = Category.objects.create(name="Private Cat", published=False)
        p1 = Programme.objects.create(title="Visible Prog", category=cat_pub, published=True)
        p2 = Programme.objects.create(title="Hidden Cat Prog", category=cat_unpub, published=True)

        response = self.client.get(reverse("sitemap"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"/training/{p1.slug}/")
        self.assertNotContains(response, f"/training/{p2.slug}/")


class UiUxOverhaulTests(TestCase):
    def setUp(self):
        self.candidate = User.objects.create_user(
            email="candidate-ui@example.com",
            password="test-pass-12345",
            first_name="Jordan",
            last_name="Lee",
            account_type=User.AccountType.CANDIDATE,
        )
        self.job = Job.objects.create(
            title="Senior SAP MM Architect",
            slug="senior-sap-mm-architect",
            location="Irving, TX (Hybrid)",
            employment_type="Full-time / Contract",
            description="Leading enterprise SAP supply chain transformation.",
            published=True,
        )

    def test_job_detail_contains_schema_org_json_ld(self):
        response = self.client.get(reverse("job_detail", args=[self.job.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '"@type": "JobPosting"')
        self.assertContains(response, "Senior SAP MM Architect")
        self.assertContains(response, '"hiringOrganization"')

    def test_candidate_dashboard_renders_pipeline_stepper(self):
        Application.objects.create(
            job=self.job,
            applicant=self.candidate,
            status=Application.Status.SHORTLISTED,
        )
        self.client.force_login(self.candidate)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Submitted")
        self.assertContains(response, "Under Review")
        self.assertContains(response, "Shortlisted")
        self.assertContains(response, "Selected")
        self.assertNotContains(response, "Active Applications")

    def test_training_verify_renders_credential_record(self):
        cat = Category.objects.create(name="Executive IT", published=True)
        prog = Programme.objects.create(title="SAP S/4HANA Masterclass", category=cat, published=True)
        reg = Registration.objects.create(programme=prog, student=self.candidate)
        reg.issue_certificate()

        response = self.client.get(reverse("verify_certificate", args=[reg.certificate_ref]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verified record")
        self.assertContains(response, "Valid certificate")
        self.assertContains(response, "Add to LinkedIn")
        self.assertContains(response, reg.certificate_ref)

    def test_enterprise_services_page_contains_faq_accordions(self):
        response = self.client.get(reverse("services"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Questions we get asked")
        self.assertContains(response, "How are the practices structured")

    def test_employers_page_contains_faq_accordions(self):
        response = self.client.get(reverse("employers"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Frequently Asked Enterprise Questions")
        self.assertContains(response, "What engagement models does GCTT support?")

    def test_theme_follows_os_preference_without_toggle(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "color-scheme")
        css = Path(settings.BASE_DIR, "static", "css", "output.css").read_text(encoding="utf-8")
        self.assertIn("prefers-color-scheme", css)
        self.assertNotContains(response, "theme-toggle-btn")
        self.assertNotContains(response, "gctt-theme")
        self.assertNotContains(response, "localStorage.getItem")


