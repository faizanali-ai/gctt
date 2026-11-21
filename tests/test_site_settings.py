from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import AuditLog, SiteSettings, User


class SiteSettingsTests(TestCase):
    def setUp(self):
        from config.site import clear_company_cache

        clear_company_cache()

    def test_defaults_are_visible_without_a_saved_row(self):
        response = self.client.get(reverse("home"))
        company = response.context["COMPANY"]
        self.assertEqual(company["name"], "GCTT")
        self.assertEqual(company["hero_cta_url"], "/employers/")
        self.assertFalse(SiteSettings.objects.exists())

    def test_saved_settings_override_the_context(self):
        SiteSettings.objects.create(
            company_name="Acme Talent",
            email="hello@acme.test",
            hero_title="Hire better builders.",
        )
        response = self.client.get(reverse("home"))
        company = response.context["COMPANY"]
        self.assertEqual(company["name"], "Acme Talent")
        self.assertEqual(company["email"], "hello@acme.test")
        self.assertEqual(company["hero_title"], "Hire better builders.")
        self.assertContains(response, "Acme Talent")
        self.assertContains(response, "Hire better builders.")
        # Unset values still fall back to the constants.
        self.assertEqual(company["legal_name"], "Global Center for Technology & Training")

    def test_singleton_save_always_uses_pk_one(self):
        SiteSettings.objects.create(company_name="First")
        SiteSettings.objects.create(company_name="Second")
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(SiteSettings.load().company_name, "Second")

    def test_settings_page_is_admin_only(self):
        staff = User.objects.create_user(
            email="staff@example.com",
            password="test-pass-12345",
            is_staff=True,
        )
        self.client.force_login(staff)
        self.assertEqual(self.client.get(reverse("manage_site_settings")).status_code, 403)

    def test_admin_can_update_settings(self):
        admin = User.objects.create_superuser(
            email="admin@example.com", password="test-pass-12345"
        )
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse("manage_site_settings")).status_code, 200)
        response = self.client.post(
            reverse("manage_site_settings"),
            {
                "company_name": "GCTT",
                "legal_name": "Global Center for Technology & Training",
                "tagline": "Technology talent and training for enterprise teams.",
                "email": "accounts@gctekton.com",
                "jobs_email": "jobs@gctekton.com",
                "address": "2612 Laramie St, Irving TX 75062",
                "url": "https://gctekton.com",
                "hero_eyebrow": "Irving, Texas",
                "hero_title": "Updated headline",
                "hero_subtitle": "Updated sub-text",
                "hero_cta_label": "Talk to us",
                "hero_cta_url": "/contact/",
            },
        )
        self.assertRedirects(response, reverse("manage_site_settings"))
        record = SiteSettings.load()
        self.assertEqual(record.hero_title, "Updated headline")
        self.assertTrue(AuditLog.objects.filter(action="settings.update").exists())


class JobTitleTests(TestCase):
    def test_profile_saves_job_title(self):
        user = User.objects.create_user(
            email="candidate@example.com", password="test-pass-12345"
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("profile"),
            {
                "first_name": "Casey",
                "last_name": "Ng",
                "phone": "+1 555 0100",
                "job_title": "SAP Consultant",
            },
        )
        self.assertRedirects(response, reverse("profile"))
        user.refresh_from_db()
        self.assertEqual(user.job_title, "SAP Consultant")

    def test_admin_user_create_and_edit_persist_job_title(self):
        admin = User.objects.create_superuser(
            email="admin@example.com", password="test-pass-12345"
        )
        self.client.force_login(admin)
        self.client.post(
            reverse("manage_user_create"),
            {
                "email": "new@example.com",
                "first_name": "New",
                "last_name": "Person",
                "phone": "",
                "job_title": "Trainer",
                "designation": "candidate",
                "password": "test-pass-12345",
                "is_active": "on",
                "email_verified": "on",
            },
        )
        created = User.objects.get(email="new@example.com")
        self.assertEqual(created.job_title, "Trainer")

        self.client.post(
            reverse("manage_user_edit", args=[created.pk]),
            {
                "email": created.email,
                "first_name": "New",
                "last_name": "Person",
                "phone": "",
                "job_title": "Senior Trainer",
                "designation": "candidate",
                "is_active": "on",
                "email_verified": "on",
            },
        )
        created.refresh_from_db()
        self.assertEqual(created.job_title, "Senior Trainer")
