import re
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.apps import assign_permissions
from apps.accounts.models import AuditLog, EmailOTP, User

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


@override_settings(REQUIRE_EMAIL_OTP=True, EMAIL_BACKEND=LOCMEM)
class EmailOTPLoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()
        cls.admin = User.objects.create_superuser(
            email="admin@example.com", password="test-pass-12345"
        )
        cls.staff = User.objects.create_user(
            email="staff@example.com",
            password="test-pass-12345",
            role=User.Role.STAFF,
            is_staff=True,
            email_verified=True,
        )
        cls.staff.groups.add(Group.objects.get(name="Recruiter"))
        cls.candidate = User.objects.create_user(
            email="candidate@example.com",
            password="test-pass-12345",
            account_type=User.AccountType.CANDIDATE,
            email_verified=True,
        )
        cls.student = User.objects.create_user(
            email="student@example.com",
            password="test-pass-12345",
            account_type=User.AccountType.STUDENT,
            email_verified=True,
        )
        cls.role_admin = User.objects.create_user(
            email="role-admin@example.com",
            password="test-pass-12345",
            role=User.Role.ADMIN,
            is_staff=False,
            email_verified=True,
        )

    def setUp(self):
        cache.clear()

    def request_code(self, email, next_url=""):
        return self.client.post(
            reverse("email_otp_request"),
            {"email": email, "next": next_url},
        )

    def code(self):
        return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)

    def test_request_page_and_login_link_render(self):
        self.assertEqual(
            self.client.get(reverse("email_otp_request")).status_code, 200
        )
        self.assertContains(
            self.client.get(reverse("login")), "one-time sign-in code"
        )

    def test_staff_email_gets_code_but_not_in_response(self):
        response = self.request_code(self.staff.email)
        self.assertRedirects(response, reverse("email_otp_verify"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.staff.email])
        code = self.code()
        self.assertNotIn(code, response.content.decode())
        self.assertTrue(
            AuditLog.objects.filter(action="auth.email_otp_request").exists()
        )

    def test_unknown_email_gets_same_response_without_email(self):
        response = self.request_code("nobody@example.com")
        self.assertRedirects(response, reverse("email_otp_verify"))
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(User.objects.filter(email="nobody@example.com").exists())
        self.assertTrue(
            AuditLog.objects.filter(
                action="auth.email_otp_request_unknown"
            ).exists()
        )

    def test_candidate_and_student_cannot_get_otp(self):
        for email in (self.candidate.email, self.student.email):
            mail.outbox.clear()
            response = self.request_code(email)
            self.assertRedirects(response, reverse("email_otp_verify"))
            self.assertEqual(len(mail.outbox), 0)
            self.client.post(reverse("email_otp_resend"))
            self.assertEqual(len(mail.outbox), 0)

    def test_admin_otp_logs_in_directly(self):
        self.request_code(self.admin.email)
        response = self.client.post(
            reverse("email_otp_verify"), {"code": self.code()}
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_staff_otp_logs_in_directly(self):
        self.request_code(self.staff.email)
        response = self.client.post(
            reverse("email_otp_verify"), {"code": self.code()}
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertIn("_auth_user_id", self.client.session)
        self.assertNotIn("pre_2fa_user_id", self.client.session)

    def test_admin_password_login_sends_code_without_asking_email(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": self.admin.email,
                "password": "test-pass-12345",
            },
        )
        self.assertRedirects(response, reverse("email_otp_verify"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.admin.email])

    def test_role_admin_without_staff_flag_requires_otp(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": self.role_admin.email,
                "password": "test-pass-12345",
            },
        )
        self.assertRedirects(response, reverse("email_otp_verify"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(mail.outbox[-1].to, [self.role_admin.email])
        response = self.client.post(
            reverse("email_otp_verify"), {"code": self.code()}
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_candidate_cannot_verify_a_code_even_if_one_exists(self):
        from apps.accounts.email_otp import issue_code

        issued = issue_code(self.candidate.email)
        self.assertIsNotNone(issued)
        session = self.client.session
        session["email_otp_email"] = self.candidate.email
        session.save()
        response = self.client.post(
            reverse("email_otp_verify"), {"code": issued[1]}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_otp_login_sends_welcome_once(self):
        self.client.post(
            reverse("login"),
            {
                "username": self.staff.email,
                "password": "test-pass-12345",
            },
        )
        self.client.post(
            reverse("email_otp_verify"), {"code": self.code()}
        )
        self.staff.refresh_from_db()
        self.assertIsNotNone(self.staff.welcome_email_sent_at)
        first_welcome_count = sum(
            "Welcome" in message.subject for message in mail.outbox
        )
        self.assertEqual(first_welcome_count, 1)

        self.client.logout()
        mail.outbox.clear()
        cache.clear()
        self.client.post(
            reverse("login"),
            {
                "username": self.staff.email,
                "password": "test-pass-12345",
            },
        )
        self.client.post(
            reverse("email_otp_verify"), {"code": self.code()}
        )
        self.assertEqual(
            sum("Welcome" in message.subject for message in mail.outbox), 0
        )

    def test_wrong_code_does_not_log_in(self):
        self.request_code(self.staff.email)
        response = self.client.post(
            reverse("email_otp_verify"), {"code": "000000"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(
            AuditLog.objects.filter(action="auth.email_otp_failed").exists()
        )

    def test_safe_next_is_respected(self):
        self.request_code(self.staff.email, next_url="/profile/")
        response = self.client.post(
            reverse("email_otp_verify"), {"code": self.code()}
        )
        self.assertRedirects(response, "/profile/")

    def test_unsafe_next_is_ignored(self):
        self.request_code(self.staff.email, next_url="https://evil.example/")
        response = self.client.post(
            reverse("email_otp_verify"), {"code": self.code()}
        )
        self.assertRedirects(response, reverse("dashboard"))

    def test_resend_respects_cooldown(self):
        self.request_code(self.staff.email)
        self.assertEqual(len(mail.outbox), 1)
        self.client.post(reverse("email_otp_resend"))
        self.assertEqual(len(mail.outbox), 1)
        cache.clear()
        self.client.post(reverse("email_otp_resend"))
        self.assertEqual(len(mail.outbox), 2)

    def test_send_failure_is_audited(self):
        with patch("apps.accounts.views.send_login_otp", return_value=False):
            response = self.request_code(self.staff.email)
        self.assertRedirects(response, reverse("email_otp_verify"))
        self.assertTrue(
            AuditLog.objects.filter(
                action="auth.email_otp_send_failed"
            ).exists()
        )
        self.assertFalse(EmailOTP.objects.filter(email=self.staff.email).exists())

    def test_reused_code_is_not_valid_after_session_clear(self):
        self.request_code(self.staff.email)
        code = self.code()
        self.client.post(reverse("email_otp_verify"), {"code": code})
        self.client.logout()
        response = self.client.post(reverse("email_otp_verify"), {"code": code})
        self.assertRedirects(response, reverse("email_otp_request"))
