from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import (
    AuditLog,
    MediaAsset,
    NavigationItem,
    PageContent,
    PageFAQ,
    SiteSettings,
    User,
)
from config.site import clear_company_cache


class SuperadminTotalControlTests(TestCase):
    def setUp(self):
        clear_company_cache()
        self.admin = User.objects.create_superuser(
            email="owner@gctekton.com",
            password="test-secure-pass-12345",
        )
        self.staff = User.objects.create_user(
            email="staff@gctekton.com",
            password="test-secure-pass-12345",
            is_staff=True,
        )
        self.candidate = User.objects.create_user(
            email="candidate@example.com",
            password="test-secure-pass-12345",
        )

    def test_pages_manager_access_control(self):
        # Anonymous redirects to login
        response = self.client.get(reverse("manage_pages"))
        self.assertEqual(response.status_code, 302)

        # Candidate gets 403
        self.client.force_login(self.candidate)
        response = self.client.get(reverse("manage_pages"))
        self.assertEqual(response.status_code, 403)

        # Standard staff without admin gets 403
        self.client.force_login(self.staff)
        response = self.client.get(reverse("manage_pages"))
        self.assertEqual(response.status_code, 403)

        # Superadmin / Owner gets 200
        self.client.force_login(self.admin)
        response = self.client.get(reverse("manage_pages"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pages &amp; website copy")
        self.assertContains(response, "About Us")
        self.assertContains(response, "Services / Talent Solutions")

    def test_admin_can_edit_page_content_and_public_site_reflects_changes(self):
        self.client.force_login(self.admin)

        # Update Home page content
        edit_url = reverse("manage_page_edit", kwargs={"page_slug": "home"})
        response = self.client.post(
            edit_url,
            {
                "title": "Custom GCTT Home Title",
                "meta_description": "Custom SEO meta description for GCTT.",
                "hero_eyebrow": "Texas Premier Talent",
                "hero_title": "Enterprise Talent & Executive Training Hub",
                "hero_subtitle": "Deploying senior practitioners across Fortune 500 accounts.",
                "hero_cta_label": "Get Immediate Talent",
                "hero_cta_url": "/employers/",
                "sections_json": '{"stats": {"placed": 1200, "retention": "98%"}}',
            },
        )
        self.assertRedirects(response, edit_url)

        # Verify database model
        pc = PageContent.objects.get(page_slug="home")
        self.assertEqual(pc.hero_title, "Enterprise Talent & Executive Training Hub")
        self.assertEqual(pc.sections_data["stats"]["placed"], 1200)
        self.assertEqual(pc.updated_by, self.admin)

        # Verify public home page renders custom text
        public_resp = self.client.get(reverse("home"))
        self.assertContains(public_resp, "Custom GCTT Home Title")
        self.assertContains(public_resp, "Enterprise Talent &amp; Executive Training Hub")
        self.assertContains(public_resp, "Texas Premier Talent")
        self.assertContains(public_resp, "Get Immediate Talent")

        # Verify audit log
        self.assertTrue(
            AuditLog.objects.filter(action="page.edit", target="home").exists()
        )

    def test_page_faq_lifecycle(self):
        self.client.force_login(self.admin)

        # Create FAQ for About page
        create_url = reverse("manage_faq_create", kwargs={"page_slug": "about"})
        response = self.client.post(
            create_url,
            {
                "page_slug": "about",
                "question": "What is the primary mission of GCTT?",
                "answer": "GCTT bridges technology talent with enterprise opportunities.",
                "order": 1,
                "is_published": True,
            },
        )
        self.assertRedirects(response, reverse("manage_page_edit", kwargs={"page_slug": "about"}))

        faq = PageFAQ.objects.get(page_slug="about")
        self.assertEqual(faq.question, "What is the primary mission of GCTT?")

        # Check public About page renders the FAQ
        about_resp = self.client.get(reverse("about"))
        self.assertContains(about_resp, "What is the primary mission of GCTT?")
        self.assertContains(about_resp, "GCTT bridges technology talent with enterprise opportunities.")

        # Edit FAQ
        edit_faq_url = reverse("manage_faq_edit", kwargs={"pk": faq.pk})
        response = self.client.post(
            edit_faq_url,
            {
                "page_slug": "about",
                "question": "Updated Mission Statement Question?",
                "answer": "Updated Answer Content.",
                "order": 2,
                "is_published": True,
            },
        )
        self.assertRedirects(response, reverse("manage_page_edit", kwargs={"page_slug": "about"}))
        faq.refresh_from_db()
        self.assertEqual(faq.question, "Updated Mission Statement Question?")

        # Delete FAQ
        delete_url = reverse("manage_faq_delete", kwargs={"pk": faq.pk})
        response = self.client.post(delete_url)
        self.assertRedirects(response, reverse("manage_page_edit", kwargs={"page_slug": "about"}))
        self.assertFalse(PageFAQ.objects.filter(pk=faq.pk).exists())

    def test_navigation_builder_lifecycle_and_fallback(self):
        self.client.force_login(self.admin)

        # Initial state: header has default divisions
        home_resp = self.client.get(reverse("home"))
        self.assertContains(home_resp, "Talent Solutions")
        self.assertContains(home_resp, "Academy")

        # Create custom navigation link
        nav_url = reverse("manage_navigation")
        response = self.client.post(
            nav_url,
            {
                "menu": "header",
                "label": "Custom Executive Portal",
                "url": "/custom-portal/",
                "order": 1,
                "is_published": True,
                "open_in_new_tab": False,
            },
        )
        self.assertRedirects(response, nav_url)

        nav_item = NavigationItem.objects.get(url="/custom-portal/")
        self.assertEqual(nav_item.label, "Custom Executive Portal")

        # Verify public site header renders custom dynamic nav item
        home_resp = self.client.get(reverse("home"))
        self.assertContains(home_resp, "Custom Executive Portal")

        # Edit navigation item
        edit_url = reverse("manage_navigation_edit", kwargs={"pk": nav_item.pk})
        response = self.client.post(
            edit_url,
            {
                "menu": "header",
                "label": "Enterprise Portal V2",
                "url": "/enterprise/",
                "order": 2,
                "is_published": True,
                "open_in_new_tab": True,
            },
        )
        self.assertRedirects(response, nav_url)
        nav_item.refresh_from_db()
        self.assertEqual(nav_item.label, "Enterprise Portal V2")

        # Delete navigation item
        del_url = reverse("manage_navigation_delete", kwargs={"pk": nav_item.pk})
        response = self.client.post(del_url)
        self.assertRedirects(response, nav_url)
        self.assertFalse(NavigationItem.objects.filter(pk=nav_item.pk).exists())

        # When table is empty, falls back safely to default navigation
        home_resp = self.client.get(reverse("home"))
        self.assertContains(home_resp, "Talent Solutions")

    def test_media_asset_library_upload_and_delete(self):
        self.client.force_login(self.admin)

        # View media library
        media_url = reverse("manage_media")
        response = self.client.get(media_url)
        self.assertEqual(response.status_code, 200)

        # Upload a test asset
        fake_file = SimpleUploadedFile("brand_banner.png", b"fake-png-content", content_type="image/png")
        response = self.client.post(
            media_url,
            {
                "title": "Spring 2027 Marketing Banner",
                "alt_text": "GCTT Spring Cohorts Banner",
                "file": fake_file,
            },
        )
        self.assertRedirects(response, media_url)

        asset = MediaAsset.objects.get(title="Spring 2027 Marketing Banner")
        self.assertEqual(asset.alt_text, "GCTT Spring Cohorts Banner")
        self.assertEqual(asset.uploaded_by, self.admin)
        self.assertTrue(asset.file_size > 0)
        self.assertTrue(asset.file.url.startswith("/media/"))

        # Delete asset
        del_url = reverse("manage_media_delete", kwargs={"pk": asset.pk})
        response = self.client.post(del_url)
        self.assertRedirects(response, media_url)
        self.assertFalse(MediaAsset.objects.filter(pk=asset.pk).exists())

    def test_announcement_banner_and_phone_settings(self):
        self.client.force_login(self.admin)

        settings_url = reverse("manage_site_settings")
        response = self.client.post(
            settings_url,
            {
                "company_name": "GCTT",
                "legal_name": "Global Center for Technology & Training",
                "tagline": "Technology talent and training for enterprise teams.",
                "email": "accounts@gctekton.com",
                "jobs_email": "jobs@gctekton.com",
                "phone": "+1 (800) 555-0199",
                "phone_raw": "+18005550199",
                "address": "2612 Laramie St, Irving TX 75062",
                "url": "https://gctekton.com",
                "hero_eyebrow": "Irving, Texas",
                "hero_title": "Enterprise Talent",
                "hero_subtitle": "Delivering across Texas.",
                "hero_cta_label": "Request talent",
                "hero_cta_url": "/employers/",
                "announcement_banner_enabled": True,
                "announcement_banner_text": "Spring 2027 Cohorts Now Open for Registration",
                "announcement_banner_link": "/training/",
            },
        )
        self.assertRedirects(response, settings_url)

        # Clear cache to ensure immediate pickup
        clear_company_cache()
        record = SiteSettings.load()
        self.assertTrue(record.announcement_banner_enabled)
        self.assertEqual(record.phone, "+1 (800) 555-0199")

        # Verify banner renders in header across pages
        home_resp = self.client.get(reverse("home"))
        self.assertContains(home_resp, "Spring 2027 Cohorts Now Open for Registration")
        self.assertContains(home_resp, "+1 (800) 555-0199")
