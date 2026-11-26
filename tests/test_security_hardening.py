from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.apps import assign_permissions
from apps.accounts.models import AuditLog, User
from apps.jobs.models import Application, Job


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AccountSecurityPageTests(TestCase):
    def test_candidate_can_open_security_page(self):
        candidate = User.objects.create_user(
            email="cand2fa@example.com", password="test-pass-12345"
        )
        self.client.force_login(candidate)
        response = self.client.get(reverse("security"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Account Security")
        self.assertNotContains(response, "Two-Factor Authentication")


class PasswordResetRateLimitTests(TestCase):
    def test_sixth_post_is_blocked(self):
        url = reverse("password_reset")
        for _ in range(5):
            response = self.client.post(
                url, {"email": "nobody@example.com"}, REMOTE_ADDR="198.51.100.55"
            )
            self.assertNotEqual(response.status_code, 403)
        response = self.client.post(
            url, {"email": "nobody@example.com"}, REMOTE_ADDR="198.51.100.55"
        )
        self.assertEqual(response.status_code, 403)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class StaffPasswordValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()
        cls.owner = User.objects.create_user(
            email="owner2@example.com",
            password="test-pass-12345",
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )

    def test_weak_password_is_rejected_on_create(self):
        self.client.force_login(self.owner)
        self.client.post(
            reverse("manage_user_create"),
            {
                "email": "weak@example.com",
                "first_name": "Weak",
                "last_name": "Pass",
                "role": User.Role.STAFF,
                "group": "Recruiter",
                "password": "12345678",
            },
        )
        self.assertFalse(User.objects.filter(email="weak@example.com").exists())

    def test_common_password_is_rejected_on_edit(self):
        target = User.objects.create_user(
            email="editme@example.com", password="test-pass-12345", role=User.Role.STAFF, is_staff=True
        )
        self.client.force_login(self.owner)
        self.client.post(
            reverse("manage_user_edit", args=[target.pk]),
            {
                "first_name": "Edit",
                "last_name": "Me",
                "role": User.Role.STAFF,
                "group": "Recruiter",
                "is_active": "on",
                "password": "password123",
            },
        )
        target.refresh_from_db()
        self.assertTrue(target.check_password("test-pass-12345"))

    def test_strong_password_is_accepted_on_edit(self):
        target = User.objects.create_user(
            email="strong@example.com", password="test-pass-12345", role=User.Role.STAFF, is_staff=True
        )
        self.client.force_login(self.owner)
        self.client.post(
            reverse("manage_user_edit", args=[target.pk]),
            {
                "first_name": "Strong",
                "last_name": "Pass",
                "role": User.Role.STAFF,
                "group": "Recruiter",
                "is_active": "on",
                "password": "Zx7!mQ2#vL9$pR4",
            },
        )
        target.refresh_from_db()
        self.assertTrue(target.check_password("Zx7!mQ2#vL9$pR4"))


class AccountDeletionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.candidate = User.objects.create_user(
            email="delete-me@example.com", password="test-pass-12345"
        )
        cls.job = Job.objects.create(title="Role", location="x", description="x", published=True)
        cls.application = Application.objects.create(
            job=cls.job, applicant=cls.candidate, resume="resumes/x.pdf"
        )
        cls.owner = User.objects.create_user(
            email="owner-del@example.com",
            password="test-pass-12345",
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )

    def test_wrong_password_keeps_account(self):
        self.client.force_login(self.candidate)
        response = self.client.post(
            reverse("account_delete"), {"password": "wrong-password"}, follow=True
        )
        self.assertContains(response, "Password incorrect")
        self.assertTrue(User.objects.filter(email="delete-me@example.com").exists())

    def test_correct_password_deletes_account_and_data(self):
        self.client.force_login(self.candidate)
        response = self.client.post(
            reverse("account_delete"), {"password": "test-pass-12345"}
        )
        self.assertRedirects(response, reverse("home"))
        self.assertFalse(User.objects.filter(email="delete-me@example.com").exists())
        self.assertFalse(Application.objects.filter(applicant_id=self.candidate.pk).exists())
        entry = AuditLog.objects.get(action="account.delete")
        self.assertEqual(entry.target, "delete-me@example.com")

    def test_owner_cannot_delete_self(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("account_delete"), {"password": "test-pass-12345"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(email="owner-del@example.com").exists())


class SecurityAndInputHardeningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()
        cls.owner = User.objects.create_user(
            email="owner-sec@example.com",
            password="test-pass-12345",
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )

    def test_admin_password_reset_clears_existing_user_sessions(self):
        from unittest.mock import patch

        from django.contrib.sessions.models import Session
        from django.test import Client

        from apps.accounts.views import _invalidate_user_sessions

        target = User.objects.create_user(
            email="session-target@example.com",
            password="test-pass-12345",
            account_type=User.AccountType.CANDIDATE,
        )
        victim_client = Client()
        victim_client.force_login(target)
        self.assertEqual(victim_client.get(reverse("dashboard")).status_code, 200)

        otp_client = Client()
        otp_session = otp_client.session
        otp_session["email_otp_user_id"] = target.pk
        otp_session["email_otp_email"] = target.email
        otp_session.save()
        otp_session_key = otp_session.session_key

        self.client.force_login(self.owner)
        with patch(
            "apps.accounts.views._invalidate_user_sessions",
            wraps=_invalidate_user_sessions,
        ) as spy_invalidate:
            self.client.post(
                reverse("manage_user_edit", args=[target.pk]),
                {
                    "email": target.email,
                    "first_name": "Target",
                    "last_name": "User",
                    "designation": "candidate",
                    "is_active": "on",
                    "password": "Zx7!mQ2#vL9$pR4",
                },
            )
        spy_invalidate.assert_called_once_with(target.pk)
        resp = victim_client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith(reverse("login")))
        self.assertFalse(Session.objects.filter(session_key=otp_session_key).exists())

    def test_account_delete_continues_when_audit_log_fails(self):
        from unittest.mock import patch

        from django.db import DatabaseError, transaction

        victim = User.objects.create_user(
            email="audit-fail-del@example.com",
            password="test-pass-12345",
            account_type=User.AccountType.CANDIDATE,
        )

        def fail_audit(*args, **kwargs):
            transaction.set_rollback(True)
            raise DatabaseError("audit table unavailable")

        self.client.force_login(victim)
        with (
            patch(
                "apps.accounts.audit.AuditLog.objects.create",
                side_effect=fail_audit,
            ),
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.client.post(
                reverse("account_delete"), {"password": "test-pass-12345"}
            )
        self.assertRedirects(response, reverse("home"))
        self.assertFalse(User.objects.filter(pk=victim.pk).exists())

    def test_site_settings_logo_urls_reject_unsafe_schemes(self):
        from apps.accounts.forms import SiteSettingsForm

        base_data = {
            "company_name": "GCTT",
            "legal_name": "GCTT",
            "tagline": "x",
            "email": "a@example.com",
            "jobs_email": "jobs@example.com",
            "address": "x",
            "url": "https://example.com",
            "hero_eyebrow": "x",
            "hero_title": "x",
            "hero_subtitle": "x",
            "hero_cta_label": "Go",
            "hero_cta_url": "/careers/",
        }
        for bad_url in (
            "javascript:alert(1)",
            "http://example.com/a.png",
            "//evil.com/a.png",
            "\\\\evil.com/a.png",
            "/\\evil.com/a.png",
            "/\t/evil.com/a.png",
            "/\n/evil.com/a.png",
            "/\r/evil.com/a.png",
        ):
            form = SiteSettingsForm(
                data={**base_data, "logo_light_url": bad_url, "logo_dark_url": bad_url}
            )
            self.assertFalse(form.is_valid())
            self.assertIn("logo_light_url", form.errors)
            self.assertIn("logo_dark_url", form.errors)

        valid_form = SiteSettingsForm(
            data={
                **base_data,
                "logo_light_url": "/static/images/logo-light.svg",
                "logo_dark_url": "https://cdn.example.com/logo-dark.svg",
            }
        )
        self.assertTrue(valid_form.is_valid(), valid_form.errors)

    def test_enquiry_initial_filters_non_form_keys_and_bounds_length(self):
        response = self.client.post(
            reverse("submit_enquiry"),
            {
                "name": "A" * 5000,
                "email": "not-an-email",
                "message": "",
                "next": "contact",
                "csrfmiddlewaretoken": "tok",
                "website": "",
                "arbitrary_injected_key": "X" * 10000,
            },
        )
        self.assertEqual(response.status_code, 302)
        saved = self.client.session.get("enquiry_initial", {})
        self.assertEqual(set(saved.keys()), {"name", "email", "message"})
        self.assertEqual(len(saved["name"]), 4000)
        self.assertNotIn("arbitrary_injected_key", saved)
        self.assertNotIn("csrfmiddlewaretoken", saved)
        self.assertNotIn("next", saved)
        self.assertNotIn("website", saved)
