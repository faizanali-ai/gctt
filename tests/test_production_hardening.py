import os
import stat
import tempfile
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser, Group, Permission
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.accounts.apps import assign_permissions
from apps.accounts.audit import log_action
from apps.accounts.forms import SiteSettingsForm
from apps.accounts.models import User
from apps.accounts.views import _validate_admin_user_fields
from apps.jobs.forms import ApplicationForm
from apps.jobs.models import Application, Job, PendingApplication
from config.emails import promotional_unsubscribe_token, send
from config.settings import validate_email_backend, validate_secret_key

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


class SettingsGuardTests(TestCase):
    def test_secret_key_must_be_non_empty_and_long(self):
        with self.assertRaises(RuntimeError):
            validate_secret_key("", debug=False, testing=False)
        with self.assertRaises(RuntimeError):
            validate_secret_key("short", debug=False, testing=False)
        with self.assertRaises(RuntimeError):
            validate_secret_key("dev-only-insecure-key-change-me", debug=False, testing=False)
        with self.assertRaises(RuntimeError):
            validate_secret_key("x" * 31, debug=False, testing=False)
        self.assertEqual(
            validate_secret_key("x" * 32, debug=False, testing=False),
            "x" * 32,
        )
        render_generated = "B0jrphAPOY7pg92AN0c9MN4yecczLMdwnx4OkA1KFUk="
        self.assertEqual(
            validate_secret_key(render_generated, debug=False, testing=False),
            render_generated,
        )

    def test_console_email_is_rejected_for_production_web(self):
        with self.assertRaises(RuntimeError):
            validate_email_backend(
                "django.core.mail.backends.console.EmailBackend",
                debug=False,
                testing=False,
                render=True,
                process_name="gunicorn",
            )
        self.assertEqual(
            validate_email_backend(
                "config.email_backends.ResendEmailBackend",
                debug=False,
                testing=False,
                render=True,
                process_name="gunicorn",
            ),
            "config.email_backends.ResendEmailBackend",
        )


class SeededOwnerTests(TestCase):
    def test_fresh_database_has_no_seeded_owner(self):
        self.assertFalse(
            User.objects.filter(
                email__in=[
                    "mohdfaizanali30@gmail.com",
                    "mohdfaizanali038@gmail.com",
                    "ceo@gctekton.com",
                ]
            ).exists()
        )

    def test_inventory_command_is_read_only(self):
        user = User.objects.create_user(email="mohdfaizanali038@gmail.com")
        output = StringIO()
        call_command("inspect_seeded_owner", stdout=output)
        self.assertIn(user.email, output.getvalue())
        self.assertTrue(User.objects.filter(pk=user.pk).exists())


class InactiveSessionTests(TestCase):
    def test_inactive_user_is_logged_out_mid_session(self):
        user = User.objects.create_user(
            email="inactive@example.com",
            password="test-pass-12345",
            is_active=True,
        )
        self.client.force_login(user)
        user.is_active = False
        user.save(update_fields=["is_active"])
        response = self.client.get(reverse("dashboard"))
        self.assertTrue(response.url.startswith(reverse("login")))
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class AdminValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            email="admin-hardening@example.com", password="test-pass-12345"
        )

    def test_invalid_admin_fields_are_rejected(self):
        errors = _validate_admin_user_fields(
            "not-an-email", "A" * 151, "B" * 151, "1" * 41, "J" * 121
        )
        self.assertEqual(len(errors), 5)

    def test_admin_create_rejects_invalid_email(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse("manage_user_create"),
            {
                "email": "not-an-email",
                "first_name": "A",
                "last_name": "B",
                "role": User.Role.STAFF,
                "group": "Recruiter",
                "password": "test-pass-12345",
                "is_active": "on",
                "email_verified": "on",
            },
        )
        self.assertFalse(User.objects.filter(first_name="A", last_name="B").exists())

    def test_admin_email_change_resets_verification(self):
        target = User.objects.create_user(
            email="old-address@example.com",
            password="test-pass-12345",
            account_type=User.AccountType.CANDIDATE,
            email_verified=True,
        )
        self.client.force_login(self.admin)
        with override_settings(EMAIL_BACKEND=LOCMEM):
            self.client.post(
                reverse("manage_user_edit", args=[target.pk]),
                {
                    "email": "new-address@example.com",
                    "first_name": "A",
                    "last_name": "B",
                    "role": "candidate",
                    "is_active": "on",
                    "email_verified": "on",
                },
            )
        target.refresh_from_db()
        self.assertEqual(target.email, "new-address@example.com")
        self.assertFalse(target.email_verified)
        self.assertTrue(
            any("new-address@example.com" in message.to for message in mail.outbox)
        )


@override_settings(EMAIL_BACKEND=LOCMEM)
class GuestApplicationValidationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.job = Job.objects.create(
            title="Platform Engineer", location="Remote", description="x", published=True
        )

    def test_41_character_phone_is_rejected_by_form(self):
        form = ApplicationForm(
            data={
                "first_name": "A",
                "last_name": "B",
                "email": "a@example.com",
                "phone": "1" * 41,
                "message": "Keen",
            },
            files={"resume": SimpleUploadedFile("cv.pdf", b"%PDF-1.4")},
            is_authenticated=False,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)

    def test_docx_resume_is_rejected(self):
        form = ApplicationForm(
            data={
                "first_name": "A",
                "last_name": "B",
                "email": "a@example.com",
                "message": "Keen",
            },
            files={"resume": SimpleUploadedFile("cv.docx", b"PK\x03\x04")},
            is_authenticated=False,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("resume", form.errors)

    def test_pending_email_cooldown_prevents_duplicate_rows(self):
        candidate = User.objects.create_user(
            email="candidate-cooldown@example.com",
            password="test-pass-12345",
            account_type=User.AccountType.CANDIDATE,
        )
        payload = {
            "first_name": "A",
            "last_name": "B",
            "email": candidate.email,
            "message": "Keen",
        }
        for _ in range(2):
            self.client.post(
                reverse("job_apply", args=[self.job.slug]),
                {**payload, "resume": SimpleUploadedFile("cv.pdf", b"%PDF-1.4")},
            )
        self.assertEqual(PendingApplication.objects.count(), 1)


@override_settings(EMAIL_BACKEND=LOCMEM, REQUIRE_VERIFIED_EMAIL_ACTIONS=True)
class VerifiedActionTests(TestCase):
    def test_unverified_candidate_cannot_apply(self):
        candidate = User.objects.create_user(
            email="unverified@example.com",
            password="test-pass-12345",
            account_type=User.AccountType.CANDIDATE,
        )
        job = Job.objects.create(
            title="Role", location="Remote", description="x", published=True
        )
        self.client.force_login(candidate)
        response = self.client.post(
            reverse("job_apply", args=[job.slug]),
            {"resume": SimpleUploadedFile("cv.pdf", b"%PDF-1.4"), "message": "Keen"},
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertFalse(Application.objects.exists())


class EmailIdempotencyTests(TestCase):
    @override_settings(EMAIL_BACKEND=LOCMEM)
    def test_retry_reuses_the_same_idempotency_key(self):
        keys = []
        real_send = mail.EmailMessage.send

        def flaky_send(self, fail_silently=False):
            keys.append(getattr(self, "idempotency_key", ""))
            if len(keys) == 1:
                raise OSError("temporary upstream timeout")
            return real_send(self, fail_silently=fail_silently)

        with patch("django.core.mail.EmailMessage.send", flaky_send):
            self.assertEqual(send("user@example.com", "Subject", "Body"), 1)
        self.assertEqual(len(keys), 2)
        self.assertTrue(keys[0])
        self.assertEqual(keys[0], keys[1])


class OpsCommandTests(TestCase):
    def test_backup_file_is_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "backup.json")
            call_command("backup_db", output=target, stdout=StringIO())
            mode = stat.S_IMODE(os.stat(target).st_mode)
            self.assertEqual(mode, 0o600)

    def test_repair_clears_direct_permissions(self):
        assign_permissions()
        staff = User.objects.create_user(
            email="direct-perm@example.com",
            password="test-pass-12345",
            is_staff=True,
            role=User.Role.STAFF,
        )
        staff.groups.add(Group.objects.get(name="Recruiter"))
        staff.user_permissions.add(
            Permission.objects.get(codename="view_application")
        )
        call_command("repair_internal_accounts", "--apply", stdout=StringIO())
        self.assertFalse(staff.user_permissions.exists())

    def test_seed_cleanup_requires_confirmation(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", "--cleanup")
        with override_settings(DEBUG=False), self.assertRaises(CommandError):
            call_command("seed_demo", "--cleanup", "--confirm")


class OneClickUnsubscribeTests(TestCase):
    def test_signed_one_click_unsubscribe(self):
        user = User.objects.create_user(
            email="unsubscribe@example.com", promotional_opt_in=True
        )
        token = promotional_unsubscribe_token(user)
        response = self.client.post(
            reverse("promotional_unsubscribe_one_click", args=[token])
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertFalse(user.promotional_opt_in)


class SmallCorrectnessTests(TestCase):
    def test_career_advisor_rejects_json_array(self):
        response = self.client.post(
            reverse("api_career_advisor"),
            data="[]",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_audit_failure_does_not_raise(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        with patch(
            "apps.accounts.audit.AuditLog.objects.create",
            side_effect=RuntimeError("audit down"),
        ):
            log_action(request, "test.action")

    def test_unsafe_hero_cta_url_is_rejected(self):
        form = SiteSettingsForm(
            data={
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
                "hero_cta_url": "javascript:alert(1)",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("hero_cta_url", form.errors)
