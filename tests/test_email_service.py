import tempfile
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

from django.apps import apps as django_apps
from django.core import mail
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.training.models import Programme
from config.emails import (
    promotional_opt_in_url,
    promotional_unsubscribe_url,
    send,
)

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


@override_settings(EMAIL_BACKEND=LOCMEM)
class WelcomeEmailTests(TestCase):
    def setUp(self):
        cache.clear()
        mail.outbox.clear()
        self.user = User.objects.create_user(
            email="welcome@example.com", password="test-pass-12345"
        )

    def login(self):
        return self.client.post(
            reverse("login"),
            {"username": self.user.email, "password": "test-pass-12345"},
        )

    def test_welcome_is_sent_only_on_first_login(self):
        self.assertRedirects(self.login(), reverse("dashboard"))
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.welcome_email_sent_at)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn("Welcome", message.subject)
        self.assertTrue(any(content_type == "text/html" for _, content_type in message.alternatives))

        self.client.logout()
        mail.outbox.clear()
        self.assertRedirects(self.login(), reverse("dashboard"))
        self.assertEqual(len(mail.outbox), 0)

    def test_profile_opt_in_requires_email_confirmation(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("profile"),
            {
                "first_name": "Jane",
                "last_name": "Doe",
                "phone": "",
                "job_title": "",
                "promotional_opt_in": "on",
            },
        )
        self.assertRedirects(response, reverse("profile"))
        self.user.refresh_from_db()
        self.assertFalse(self.user.promotional_opt_in)
        self.assertIsNotNone(self.user.promotional_opt_in_requested_at)
        confirmation = next(
            message for message in mail.outbox if "email preferences" in message.subject.lower()
        )
        self.assertTrue(any(content_type == "text/html" for _, content_type in confirmation.alternatives))

        url = promotional_opt_in_url(self.user)
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, url.rsplit("https://gctekton.com", 1)[-1])
        self.user.refresh_from_db()
        self.assertTrue(self.user.promotional_opt_in)
        self.assertIsNotNone(self.user.promotional_opt_in_at)
        self.assertIsNone(self.user.promotional_opt_in_requested_at)

    def test_signup_opt_in_sends_confirmation_only(self):
        cache.clear()
        response = self.client.post(
            reverse("signup"),
            {
                "account_type": "candidate",
                "email": "signup-offers@example.com",
                "first_name": "Signup",
                "last_name": "Offers",
                "password1": "test-pass-12345",
                "password2": "test-pass-12345",
                "promotional_opt_in": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="signup-offers@example.com")
        self.assertFalse(user.promotional_opt_in)
        self.assertIsNotNone(user.promotional_opt_in_requested_at)
        self.assertTrue(
            any("email preferences" in message.subject.lower() for message in mail.outbox)
        )

    def test_welcome_backfill_marks_existing_logged_in_users(self):
        existing = User.objects.create_user(
            email="existing@example.com", password="test-pass-12345"
        )
        existing.last_login = timezone.now()
        existing.save(update_fields=["last_login"])
        migration = import_module(
            "apps.accounts.migrations.0013_user_promotional_opt_in_user_promotional_opt_in_at_and_more"
        )
        migration.backfill_welcome_state(django_apps, None)
        existing.refresh_from_db()
        self.assertIsNotNone(existing.welcome_email_sent_at)

    def test_welcome_failure_can_retry_on_next_login(self):
        with patch("config.emails.send", return_value=0):
            self.login()
        self.user.refresh_from_db()
        self.assertIsNone(self.user.welcome_email_sent_at)
        self.client.logout()
        mail.outbox.clear()
        self.login()
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.welcome_email_sent_at)
        self.assertEqual(len(mail.outbox), 1)


@override_settings(EMAIL_BACKEND=LOCMEM)
class EmailRetryTests(TestCase):
    @override_settings(EMAIL_BACKEND=LOCMEM, EMAIL_RETRY_DELAY_SECONDS=0)
    def test_transient_failure_is_retried_once(self):
        with patch.object(
            EmailMultiAlternatives, "send", side_effect=[OSError("temporary"), 1]
        ) as mocked:
            self.assertEqual(send("retry@example.com", "Retry", "Body"), 1)
        self.assertEqual(mocked.call_count, 2)


class EnrollmentEmailTests(TestCase):
    def setUp(self):
        cache.clear()
        mail.outbox.clear()
        self.student = User.objects.create_user(
            email="student@example.com",
            password="test-pass-12345",
            account_type=User.AccountType.STUDENT,
        )
        self.programme = Programme.objects.create(
            title="SAP Basics",
            description="x",
            published=True,
            registration_open=True,
        )

    def test_registration_sends_html_and_text_enrollment_email(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse("programme_register", args=[self.programme.slug]),
            {"message": "Please enroll me"},
        )
        self.assertEqual(response.status_code, 302)
        message = next(m for m in mail.outbox if "Registration received" in m.subject)
        self.assertEqual(message.to, [self.student.email])
        self.assertIn(self.programme.title, message.body)
        self.assertTrue(any(content_type == "text/html" for _, content_type in message.alternatives))


@override_settings(EMAIL_BACKEND=LOCMEM)
class PromotionalEmailTests(TestCase):
    def setUp(self):
        cache.clear()
        mail.outbox.clear()
        self.user = User.objects.create_user(
            email="offers@example.com",
            password="test-pass-12345",
            promotional_opt_in=True,
        )
        self.body_file = Path(tempfile.mkstemp(suffix=".txt")[1])
        self.body_file.write_text("A new SAP cohort is open.", encoding="utf-8")

    def tearDown(self):
        self.body_file.unlink(missing_ok=True)

    def test_second_batch_continues_after_the_first(self):
        second = User.objects.create_user(
            email="offers-two@example.com",
            password="test-pass-12345",
            promotional_opt_in=True,
        )
        call_command(
            "send_promotional",
            "--subject",
            "New cohort",
            "--body-file",
            str(self.body_file),
            "--send",
            "--sleep",
            "0",
            "--limit",
            "1",
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        mail.outbox.clear()
        call_command(
            "send_promotional",
            "--subject",
            "New cohort",
            "--body-file",
            str(self.body_file),
            "--send",
            "--sleep",
            "0",
            "--limit",
            "1",
            "--after-id",
            str(self.user.pk),
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [second.email])

    def test_invalid_command_options_are_rejected(self):
        with self.assertRaises(CommandError):
            call_command(
                "send_promotional",
                "--subject",
                "New cohort",
                "--body-file",
                str(self.body_file),
                "--sleep",
                "-1",
            )
        with self.assertRaises(CommandError):
            call_command(
                "send_promotional",
                "--subject",
                "",
                "--body-file",
                str(self.body_file),
            )

    def test_dry_run_sends_nothing(self):
        call_command(
            "send_promotional",
            "--subject",
            "New cohort",
            "--body-file",
            str(self.body_file),
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_send_only_reaches_confirmed_opted_in_users(self):
        User.objects.create_user(
            email="no-offers@example.com", password="test-pass-12345"
        )
        User.objects.create_user(
            email="pending-offers@example.com",
            password="test-pass-12345",
            promotional_opt_in=False,
            promotional_opt_in_requested_at=timezone.now(),
        )
        call_command(
            "send_promotional",
            "--subject",
            "New cohort",
            "--body-file",
            str(self.body_file),
            "--send",
            "--sleep",
            "0",
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertIn("List-Unsubscribe", mail.outbox[0].extra_headers)
        self.assertTrue(any(content_type == "text/html" for _, content_type in mail.outbox[0].alternatives))

    def test_failure_stops_the_batch_before_advancing(self):
        from unittest.mock import MagicMock

        from django.core.management import call_command

        second = User.objects.create_user(
            email="offers-two@example.com",
            password="test-pass-12345",
            promotional_opt_in=True,
        )
        User.objects.create_user(
            email="offers-three@example.com",
            password="test-pass-12345",
            promotional_opt_in=True,
        )
        mocked = MagicMock(side_effect=[True, False, True])
        with patch(
            "apps.accounts.management.commands.send_promotional.send_promotional",
            mocked,
        ):
            call_command(
                "send_promotional",
                "--subject",
                "New cohort",
                "--body-file",
                str(self.body_file),
                "--send",
                "--sleep",
                "0",
                "--limit",
                "3",
            )
        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(second.pk, mocked.call_args_list[1].args[0].pk)

    def test_unsubscribe_link_disables_promotional_mail(self):
        url = promotional_unsubscribe_url(self.user)
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, url.rsplit("https://gctekton.com", 1)[-1])
        self.user.refresh_from_db()
        self.assertFalse(self.user.promotional_opt_in)

        mail.outbox.clear()
        call_command(
            "send_promotional",
            "--subject",
            "New cohort",
            "--body-file",
            str(self.body_file),
            "--send",
            "--sleep",
            "0",
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_opt_in_confirmation_token_is_rejected(self):
        response = self.client.get(
            reverse("promotional_opt_in_confirm", args=["not-a-token"])
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_unsubscribe_token_is_rejected(self):
        response = self.client.get(
            reverse("promotional_unsubscribe", args=["not-a-token"])
        )
        self.assertEqual(response.status_code, 400)
