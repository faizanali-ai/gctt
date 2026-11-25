import fcntl
import os
import stat
import subprocess
import sys
import tempfile
import threading
import time
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


class PipelineHardeningTests(TestCase):
    def test_wake_is_exempt_from_ssl_redirect(self):
        with override_settings(
            SECURE_SSL_REDIRECT=True,
            SECURE_REDIRECT_EXEMPT=[r"^wake/$"],
        ):
            wake_resp = self.client.get(reverse("wake"))
            health_resp = self.client.get(reverse("healthz"))
        self.assertEqual(wake_resp.status_code, 200)
        self.assertEqual(wake_resp.content, b"ok")
        self.assertEqual(health_resp.status_code, 301)

    def test_production_settings_define_wake_redirect_exempt(self):
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in {"DATABASE_URL", "RENDER"}
        }
        env.update(
            {
                "DJANGO_DEBUG": "0",
                "DJANGO_SECRET_KEY": "ci-only-secret-9f8e7d6c5b4a39281706f5e4d3c2b1a0f9e8d7c6b5a49382",
                "DATABASE_URL": "sqlite:///db.sqlite3",
                "EMAIL_BACKEND": "config.email_backends.ResendEmailBackend",
            }
        )
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); "
                    "from django.conf import settings; print(settings.SECURE_REDIRECT_EXEMPT)"
                ),
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("^wake/$", proc.stdout)

    def test_collectstatic_succeeds_without_runtime_db_or_storage(self):
        env = {
            k: v
            for k, v in os.environ.items()
            if k
            not in {
                "DATABASE_URL",
                "R2_BUCKET",
                "R2_ENDPOINT",
                "R2_ACCESS_KEY_ID",
                "R2_SECRET_ACCESS_KEY",
                "SUPABASE_URL",
                "SUPABASE_BUCKET",
                "SUPABASE_REGION",
                "SUPABASE_ACCESS_KEY_ID",
                "SUPABASE_SECRET_ACCESS_KEY",
            }
        }
        env.update(
            {
                "DJANGO_DEBUG": "0",
                "DJANGO_SECRET_KEY": "ci-only-secret-9f8e7d6c5b4a39281706f5e4d3c2b1a0f9e8d7c6b5a49382",
                "RENDER": "1",
                "EMAIL_BACKEND": "config.email_backends.ResendEmailBackend",
            }
        )
        proc = subprocess.run(
            [
                sys.executable,
                "manage.py",
                "collectstatic",
                "--noinput",
                "--dry-run",
                "--ignore=input.css",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_non_collectstatic_production_still_fails_without_db_and_storage(self):
        base_env = {
            k: v
            for k, v in os.environ.items()
            if k
            not in {
                "DATABASE_URL",
                "R2_BUCKET",
                "SUPABASE_URL",
                "RENDER",
            }
        }
        base_env.update(
            {
                "DJANGO_DEBUG": "0",
                "DJANGO_SECRET_KEY": "ci-only-secret-9f8e7d6c5b4a39281706f5e4d3c2b1a0f9e8d7c6b5a49382",
                "EMAIL_BACKEND": "config.email_backends.ResendEmailBackend",
            }
        )
        no_db = subprocess.run(
            [sys.executable, "manage.py", "check"],
            env=base_env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(no_db.returncode, 0)
        self.assertIn("DATABASE_URL is required", no_db.stderr)

        no_storage_env = {
            **base_env,
            "DATABASE_URL": "sqlite:///db.sqlite3",
            "RENDER": "1",
        }
        no_storage = subprocess.run(
            [sys.executable, "manage.py", "check"],
            env=no_storage_env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(no_storage.returncode, 0)
        self.assertIn("Production media storage is not configured", no_storage.stderr)

    def test_generate_certificate_pdf_serializes_with_flock_and_unlocks_on_error(self):
        from apps.training.certificates import generate_certificate_pdf
        from apps.training.models import Programme, Registration

        student = User.objects.create_user(
            email="cert-lock@example.com",
            password="test-pass-12345",
            account_type=User.AccountType.STUDENT,
        )
        programme = Programme.objects.create(
            title="Lock Test", description="x", published=True
        )
        reg = Registration.objects.create(programme=programme, student=student)

        active = 0
        max_active = 0
        counter_lock = threading.Lock()

        class FakeHTML:
            def __init__(self, string, base_url):
                self.string = string

            def write_pdf(self, target):
                nonlocal active, max_active
                with counter_lock:
                    active += 1
                    max_active = max(max_active, active)
                time.sleep(0.05)
                target.write(b"%PDF-1.4")
                with counter_lock:
                    active -= 1

        with patch("apps.training.certificates.HTML", FakeHTML):
            threads = [
                threading.Thread(target=generate_certificate_pdf, args=(reg,))
                for _ in range(2)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        self.assertEqual(max_active, 1)

        flock_ops = []
        real_flock = fcntl.flock

        def recording_flock(fd, op):
            flock_ops.append(op)
            return real_flock(fd, op)

        class FailingHTML:
            def __init__(self, string, base_url):
                pass

            def write_pdf(self, target):
                raise RuntimeError("weasyprint boom")

        with (
            patch("apps.training.certificates.HTML", FailingHTML),
            patch("apps.training.certificates.fcntl.flock", recording_flock),
            self.assertRaises(RuntimeError),
        ):
            generate_certificate_pdf(reg)

        self.assertEqual(flock_ops, [fcntl.LOCK_EX, fcntl.LOCK_UN])
