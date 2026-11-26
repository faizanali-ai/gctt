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

    def test_svg_with_whitespace_event_handler_is_rejected(self):
        svg_with_whitespace = b'<svg xmlns="http://www.w3.org/2000/svg" onload = "alert(1)"><circle r="10"/></svg>'
        upload = SimpleUploadedFile("whitespace_handler.svg", svg_with_whitespace, content_type="image/svg+xml")
        response = self.client.post(
            reverse("manage_media"),
            {"title": "Whitespace Handler SVG", "file": upload, "alt_text": "Test"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(MediaAsset.objects.filter(title="Whitespace Handler SVG").exists())
        self.assertContains(response, "SVG contains unsafe script elements")

    def test_svg_with_foreign_object_is_rejected(self):
        svg_with_foreign = b'<svg xmlns="http://www.w3.org/2000/svg"><foreignObject><iframe src="https://evil.com"/></foreignObject></svg>'
        upload = SimpleUploadedFile("foreign.svg", svg_with_foreign, content_type="image/svg+xml")
        response = self.client.post(
            reverse("manage_media"),
            {"title": "Foreign Object SVG", "file": upload, "alt_text": "Test"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(MediaAsset.objects.filter(title="Foreign Object SVG").exists())
        self.assertContains(response, "SVG contains unsafe script elements")

    def test_media_asset_serve_sets_csp_for_svg(self):
        safe_svg = b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="10"/></svg>'
        asset = MediaAsset.objects.create(
            title="Safe Icon",
            file=SimpleUploadedFile("icon.svg", safe_svg, content_type="image/svg+xml"),
            uploaded_by=self.admin,
        )
        response = self.client.get(reverse("media_asset_serve", args=[asset.pk]))
        self.assertEqual(response["Content-Security-Policy"], "default-src 'none'; style-src 'unsafe-inline'")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_media_asset_serve_missing_svg_returns_404_on_remote_storage(self):
        from unittest.mock import MagicMock, patch

        safe_svg = b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="10"/></svg>'
        asset = MediaAsset.objects.create(
            title="Remote SVG",
            file=SimpleUploadedFile("remote.svg", safe_svg, content_type="image/svg+xml"),
            uploaded_by=self.admin,
        )
        fake_storage = MagicMock()
        fake_storage.open.side_effect = FileNotFoundError("missing on S3")
        with (
            patch("django.core.files.storage.default_storage", fake_storage),
            patch("django.db.models.fields.files.FieldFile.open", side_effect=FileNotFoundError("missing on S3")),
        ):
            response = self.client.get(reverse("media_asset_serve", args=[asset.pk]))
        self.assertEqual(response.status_code, 404)

    def test_svg_with_encoded_tab_in_href_is_rejected(self):
        svg_with_tab = b'<svg xmlns="http://www.w3.org/2000/svg"><a href="java&#x09;script:alert(1)"><text>x</text></a></svg>'
        upload = SimpleUploadedFile("tab_exploit.svg", svg_with_tab, content_type="image/svg+xml")
        response = self.client.post(
            reverse("manage_media"),
            {"title": "Tab Exploit SVG", "file": upload, "alt_text": "Test"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(MediaAsset.objects.filter(title="Tab Exploit SVG").exists())
        self.assertContains(response, "SVG contains unsafe script elements")

    def test_svg_with_xml_entity_is_rejected_without_500(self):
        xxe_svg = b'<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe "test">]><svg xmlns="http://www.w3.org/2000/svg">&xxe;</svg>'
        upload = SimpleUploadedFile("xxe.svg", xxe_svg, content_type="image/svg+xml")
        response = self.client.post(
            reverse("manage_media"),
            {"title": "XXE SVG", "file": upload, "alt_text": "Test"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(MediaAsset.objects.filter(title="XXE SVG").exists())
        self.assertContains(response, "SVG contains unsafe XML entities")


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

    def test_navigation_delete_returns_deletion_result(self):
        item = NavigationItem.objects.create(menu="header", label="Temp", url="/temp/", order=99)
        count, details = item.delete()
        self.assertEqual(count, 1)
        self.assertIn("accounts.NavigationItem", details)


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

    def tearDown(self):
        clear_company_cache()

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

    def test_applied_candidate_sees_dashboard_link_when_applications_paused(self):
        Application.objects.create(
            job=self.job,
            applicant=self.candidate,
        )
        settings = SiteSettings.load()
        settings.allow_candidate_applications = False
        settings.save()
        clear_company_cache()

        self.client.force_login(self.candidate)
        response = self.client.get(reverse("job_detail", args=[self.job.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You have already applied for this role.")
        self.assertContains(response, "Open candidate dashboard")
        self.assertNotContains(response, "Applications are temporarily paused")

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
