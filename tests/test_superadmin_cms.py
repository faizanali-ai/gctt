"""Comprehensive production tests for Superadmin Total Control, Media Hardening, and Intake Gating."""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import (
    MediaAsset,
    NavigationItem,
    PageContent,
    PageFAQ,
    SiteSettings,
    User,
)
from apps.jobs.models import Application, Job
from apps.training.models import Programme, Registration
from config.context_processors import _get_dynamic_nav, clear_navigation_cache
from config.site import clear_company_cache


class MediaAssetHardeningTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin.cms@example.com", password="test-pass-12345", role=User.Role.ADMIN
        )
        self.client.force_login(self.admin)

    def test_malicious_svg_with_script_is_rejected(self):
        malicious_svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        upload = SimpleUploadedFile("exploit.svg", malicious_svg, content_type="image/svg+xml")
        response = self.client.post(
            reverse("manage_media"),
            {"title": "Malicious SVG", "file": upload, "alt_text": "Test"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(MediaAsset.objects.filter(title="Malicious SVG").exists())
        self.assertContains(response, "SVG contains unsafe script elements")

    def test_safe_png_is_accepted_with_opaque_filename(self):
        valid_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        upload = SimpleUploadedFile("logo.png", valid_png, content_type="image/png")
        response = self.client.post(
            reverse("manage_media"),
            {"title": "Company Logo", "file": upload, "alt_text": "Company Logo"},
        )
        self.assertRedirects(response, reverse("manage_media"))
        asset = MediaAsset.objects.get(title="Company Logo")
        self.assertRegex(asset.file.name, r"^media/[0-9a-f]{32}\.png$")

    def test_oversized_file_is_rejected(self):
        oversized = b"\x89PNG\r\n\x1a\n" + b"0" * (11 * 1024 * 1024)
        upload = SimpleUploadedFile("huge.png", oversized, content_type="image/png")
        response = self.client.post(
            reverse("manage_media"),
            {"title": "Huge Asset", "file": upload},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(MediaAsset.objects.filter(title="Huge Asset").exists())


class DynamicNavCachingTests(TestCase):
    def setUp(self):
        clear_navigation_cache()

    def tearDown(self):
        clear_navigation_cache()

    def test_navigation_query_is_cached(self):
        NavigationItem.objects.create(menu="header", label="Docs", url="/docs/", order=1, is_published=True)
        with self.assertNumQueries(1):
            _get_dynamic_nav()
        with self.assertNumQueries(0):
            _get_dynamic_nav()

    def test_clear_cache_invalidates(self):
        _get_dynamic_nav()
        clear_navigation_cache()
        with self.assertNumQueries(1):
            _get_dynamic_nav()


class IntakeGatingTests(TestCase):
    def setUp(self):
        clear_company_cache()
        self.candidate = User.objects.create_user(
            email="candidate@example.com", password="test-pass-12345", account_type=User.AccountType.CANDIDATE
        )
        self.job = Job.objects.create(title="DevOps Engineer", location="Remote", description="Job", published=True)
        self.programme = Programme.objects.create(
            title="Cloud Architect", description="Course", published=True, registration_open=True
        )

    def test_candidate_applications_toggle_pauses_apply(self):
        settings = SiteSettings.load()
        settings.allow_candidate_applications = False
        settings.save()
        clear_company_cache()

        self.client.force_login(self.candidate)
        dummy_pdf = SimpleUploadedFile("cv.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        response = self.client.post(
            reverse("job_apply", args=[self.job.slug]),
            {"resume": dummy_pdf, "message": "Applying for this role"},
        )
        self.assertRedirects(response, reverse("job_detail", args=[self.job.slug]))
        self.assertFalse(Application.objects.exists())

    def test_student_registrations_toggle_pauses_register(self):
        settings = SiteSettings.load()
        settings.allow_student_registrations = False
        settings.save()
        clear_company_cache()

        student = User.objects.create_user(
            email="student@example.com", password="test-pass-12345", account_type=User.AccountType.STUDENT
        )
        self.client.force_login(student)
        response = self.client.post(
            reverse("programme_register", args=[self.programme.slug]),
            {"message": "Enroll me in cohort"},
        )
        self.assertRedirects(response, reverse("programme_detail", args=[self.programme.slug]))
        self.assertFalse(Registration.objects.exists())


class PageAndFAQTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin.pages@example.com", password="test-pass-12345", role=User.Role.ADMIN
        )
        self.client.force_login(self.admin)

    def test_edit_page_content_and_create_faq(self):
        response = self.client.post(
            reverse("manage_page_edit", args=["services"]),
            {
                "hero_eyebrow": "Enterprise Solutions",
                "hero_title": "Custom Staffing & Advisory",
                "hero_subtitle": "Delivering exceptional tech leaders.",
                "hero_cta_label": "Get in touch",
                "hero_cta_url": "/contact/",
            },
        )
        self.assertRedirects(response, reverse("manage_page_edit", args=["services"]))
        pc = PageContent.objects.get(page_slug="services")
        self.assertEqual(pc.hero_title, "Custom Staffing & Advisory")

        faq_response = self.client.post(
            reverse("manage_faq_create", args=["services"]),
            {
                "page_slug": "services",
                "question": "What is the onboarding SLA?",
                "answer": "Under 48 hours for pre-vetted engineers.",
                "order": 1,
                "is_published": "on",
            },
        )
        self.assertRedirects(faq_response, reverse("manage_page_edit", args=["services"]))
        self.assertTrue(PageFAQ.objects.filter(question="What is the onboarding SLA?").exists())
