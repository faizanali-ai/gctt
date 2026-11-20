import re
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts.apps import assign_permissions
from apps.accounts.models import AuditLog, User

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


@override_settings(EMAIL_BACKEND=LOCMEM)
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

    def setUp(self):
        cache.clear()

    def request_code(self, email, next_url=""):
        return self.client.post(
            reverse("email_otp_request"),
            {"email": email, "next": next_url},
        )

    def code(self):
        return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)

    def verify(self, code, email="candidate@example.com"):
        self.request_code(email)
        return self.client.post(reverse("email_otp_verify"), {"code": code})

    def test_request_page_and_login_link_render(self):
        self.assertEqual(
            self.client.get(reverse("email_otp_request")).status_code, 200
        )
        self.assertContains(
            self.client.get(reverse("login")), "one-time sign-in code"
        )

    def test_existing_email_gets_code_but_not_in_response(self):
        response = self.request_code(self.candidate.email)
        self.assertRedirects(response, reverse("email_otp_verify"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.candidate.email])
        code = self.code()
        self.assertNotIn(code, response.content.decode())
        self.assertTrue(
            AuditLog.objects.filter(action="auth.email_otp_request").exists()
        )

    def test_unverified_external_account_gets_no_code(self):
        User.objects.create_user(
            email="unverified@example.com",
            password="test-pass-12345",
            email_verified=False,
        )
        response = self.request_code("unverified@example.com")
        self.assertRedirects(response, reverse("email_otp_verify"))
        self.assertEqual(len(mail.outbox), 0)

    def test_send_failure_is_audited_without_leaking_code(self):
        with patch(
            "apps.accounts.views.send_login_otp", return_value=False
        ):
            response = self.request_code(self.candidate.email)
        self.assertRedirects(response, reverse("email_otp_verify"))
        self.assertTrue(
            AuditLog.objects.filter(
                action="auth.email_otp_send_failed"
            ).exists()
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

    def test_candidate_logs_in_and_routes_to_dashboard(self):
        self.request_code(self.candidate.email)
        response = self.client.post(
            reverse("email_otp_verify"), {"code": self.code()}
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertIn("_auth_user_id", self.client.session)
        self.candidate.refresh_from_db()
        self.assertTrue(self.candidate.email_verified)
        self.assertTrue(AuditLog.objects.filter(action="auth.email_otp").exists())

    def test_student_logs_in_and_sees_registration_dashboard(self):
        self.request_code(self.student.email)
        response = self.client.post(
            reverse("email_otp_verify"), {"code": self.code()}, follow=True
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertIn("_auth_user_id", self.client.session)
        self.assertIn("registrations", response.context)

    def test_admin_logs_in_and_routes_to_dashboard(self):
        self.request_code(self.admin.email)
        response = self.client.post(
            reverse("email_otp_verify"), {"code": self.code()}
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_admin_otp_skips_totp_even_when_device_exists(self):
        TOTPDevice.objects.create(user=self.admin, name="default", confirmed=True)
        self.request_code(self.admin.email)
        response = self.client.post(
            reverse("email_otp_verify"), {"code": self.code()}
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_admin_password_login_redirects_to_email_otp(self):
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

    def test_candidate_password_login_is_unchanged(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": self.candidate.email,
                "password": "test-pass-12345",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_admin_pending_2fa_session_is_sent_to_email_otp(self):
        session = self.client.session
        session["pre_2fa_user_id"] = self.admin.pk
        session.save()
        response = self.client.get(reverse("login_2fa"))
        self.assertRedirects(response, reverse("email_otp_verify"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("pre_2fa_user_id", self.client.session)

    def test_staff_with_totp_is_challenged_not_logged_in(self):
        TOTPDevice.objects.create(user=self.staff, name="default", confirmed=True)
        self.request_code(self.staff.email)
        response = self.client.post(
            reverse("email_otp_verify"), {"code": self.code()}
        )
        self.assertRedirects(response, reverse("login_2fa"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(
            self.client.session["pre_2fa_user_id"], self.staff.pk
        )


    @override_settings(REQUIRE_STAFF_2FA=True)
    def test_staff_without_totp_is_sent_to_enrollment(self):
        self.request_code(self.staff.email)
        response = self.client.post(
            reverse("email_otp_verify"), {"code": self.code()}
        )
        self.assertRedirects(
            response, reverse("login_2fa"), fetch_redirect_response=False
        )
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.get(reverse("login_2fa"))
        self.assertRedirects(response, reverse("login_2fa_enroll"))

    def test_wrong_code_does_not_log_in(self):
        self.request_code(self.candidate.email)
        response = self.client.post(
            reverse("email_otp_verify"), {"code": "000000"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(
            AuditLog.objects.filter(action="auth.email_otp_failed").exists()
        )

    def test_safe_next_is_respected(self):
        self.request_code(self.candidate.email, next_url="/profile/")
        response = self.client.post(
            reverse("email_otp_verify"), {"code": self.code()}
        )
        self.assertRedirects(response, "/profile/")

    def test_unsafe_next_is_ignored(self):
        self.request_code(self.candidate.email, next_url="https://evil.example/")
        response = self.client.post(
            reverse("email_otp_verify"), {"code": self.code()}
        )
        self.assertRedirects(response, reverse("dashboard"))

    def test_resend_respects_cooldown(self):
        self.request_code(self.candidate.email)
        self.assertEqual(len(mail.outbox), 1)
        self.client.post(reverse("email_otp_resend"))
        self.assertEqual(len(mail.outbox), 1)
        cache.clear()
        self.client.post(reverse("email_otp_resend"))
        self.assertEqual(len(mail.outbox), 2)

    def test_reused_code_is_not_valid_after_session_clear(self):
        self.request_code(self.candidate.email)
        code = self.code()
        self.client.post(reverse("email_otp_verify"), {"code": code})
        self.client.logout()
        response = self.client.post(reverse("email_otp_verify"), {"code": code})
        self.assertRedirects(response, reverse("email_otp_request"))
