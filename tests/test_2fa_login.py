from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


@override_settings(EMAIL_BACKEND=LOCMEM)
class LoginFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            email="admin@example.com", password="test-pass-12345"
        )
        cls.staff = User.objects.create_user(
            email="staff@example.com",
            password="test-pass-12345",
            role=User.Role.STAFF,
            is_staff=True,
        )
        cls.candidate = User.objects.create_user(
            email="candidate@example.com", password="test-pass-12345"
        )

    def setUp(self):
        cache.clear()

    def login(self, email):
        return self.client.post(
            reverse("login"),
            {"username": email, "password": "test-pass-12345"},
        )

    def test_staff_password_login_without_otp_logs_in(self):
        response = self.login(self.staff.email)
        self.assertRedirects(response, reverse("dashboard"))
        self.assertIn("_auth_user_id", self.client.session)

    @override_settings(REQUIRE_EMAIL_OTP=True)
    def test_staff_password_login_with_otp_sends_code(self):
        response = self.login(self.staff.email)
        self.assertRedirects(response, reverse("email_otp_verify"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.staff.email])

    def test_admin_password_login_without_otp_logs_in(self):
        response = self.login(self.admin.email)
        self.assertRedirects(response, reverse("dashboard"))
        self.assertIn("_auth_user_id", self.client.session)

    @override_settings(REQUIRE_EMAIL_OTP=True)
    def test_admin_password_login_with_otp_sends_code(self):
        response = self.login(self.admin.email)
        self.assertRedirects(response, reverse("email_otp_verify"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(REQUIRE_EMAIL_OTP=True)
    def test_candidate_password_login_is_unchanged(self):
        response = self.login(self.candidate.email)
        self.assertRedirects(response, reverse("dashboard"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_old_2fa_url_redirects_to_login(self):
        response = self.client.get(reverse("login_2fa"))
        self.assertRedirects(response, reverse("login"))

    def test_email_otp_link_and_page_are_disabled_by_default(self):
        self.assertNotContains(
            self.client.get(reverse("login")), "one-time sign-in code"
        )
        self.assertRedirects(
            self.client.get(reverse("email_otp_request")), reverse("login")
        )
