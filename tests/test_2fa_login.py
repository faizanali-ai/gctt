from django.test import TestCase
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.oath import totp

from apps.accounts.models import User


class TwoFactorPreAuthLoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="faizan.test@gctekton.com",
            password="securePassword123!",
            role=User.Role.STAFF,
        )
        self.user.email_verified = True
        self.user.is_staff = True
        self.user.save()

    def _token(self, device):
        return totp(device.bin_key, device.step, device.t0, device.digits)

    def test_login_without_2fa_logs_in_directly(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.user.email, "password": "securePassword123!"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.id)

    def test_login_with_2fa_requires_code_before_authenticating(self):
        device = self.user.totpdevice_set.create(name="default", confirmed=True)

        # Step 1: Submit email & password
        response = self.client.post(
            reverse("login"),
            {"username": self.user.email, "password": "securePassword123!"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("login_2fa"))

        # User MUST NOT be authenticated yet
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.session.get("pre_2fa_user_id"), self.user.id)

        # Protected pages must deny access because user is not logged in
        dash_res = self.client.get(reverse("dashboard"))
        self.assertEqual(dash_res.status_code, 302)
        self.assertIn(reverse("login"), dash_res.url)

        # Step 2: Submit valid 6-digit code
        valid_res = self.client.post(reverse("login_2fa"), {"token": self._token(device)})
        self.assertEqual(valid_res.status_code, 302)
        self.assertEqual(valid_res.url, reverse("dashboard"))

        # User IS authenticated and verified
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.id)
        self.assertEqual(self.client.session[DEVICE_ID_SESSION_KEY], device.persistent_id)

    def test_login_2fa_invalid_token_is_rejected(self):
        self.user.totpdevice_set.create(name="default", confirmed=True)

        self.client.post(
            reverse("login"),
            {"username": self.user.email, "password": "securePassword123!"},
        )
        self.assertEqual(self.client.session.get("pre_2fa_user_id"), self.user.id)

        bad_res = self.client.post(reverse("login_2fa"), {"token": "000000"})
        self.assertEqual(bad_res.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(bad_res, "Invalid 6-digit verification code")

    def test_login_2fa_cancel_clears_pre_auth_state(self):
        self.user.totpdevice_set.create(name="default", confirmed=True)

        self.client.post(
            reverse("login"),
            {"username": self.user.email, "password": "securePassword123!"},
        )
        self.assertEqual(self.client.session.get("pre_2fa_user_id"), self.user.id)

        cancel_res = self.client.post(reverse("login_2fa"), {"action": "cancel"})
        self.assertEqual(cancel_res.status_code, 302)
        self.assertEqual(cancel_res.url, reverse("login"))
        self.assertNotIn("pre_2fa_user_id", self.client.session)
