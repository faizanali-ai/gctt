import json
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User


class GoogleOAuthTests(TestCase):
    def setUp(self):
        self.owner = User.objects.filter(email="mohdfaizanali038@gmail.com").first()
        if not self.owner:
            self.owner = User.objects.create_superuser(
                email="mohdfaizanali038@gmail.com",
                password="testpassword123",
                role=User.Role.ADMIN,
            )

    def test_google_login_redirects_when_not_configured(self):
        with override_settings(GOOGLE_CLIENT_ID="", GOOGLE_CLIENT_SECRET=""):
            response = self.client.get(reverse("google_login"))
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse("login"))

    @override_settings(GOOGLE_CLIENT_ID="mock-client-id", GOOGLE_CLIENT_SECRET="mock-client-secret")
    def test_google_login_redirects_to_google_endpoint(self):
        response = self.client.get(reverse("google_login") + "?next=/dashboard/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("accounts.google.com/o/oauth2/v2/auth", response.url)
        self.assertIn("client_id=mock-client-id", response.url)
        self.assertIn("google_oauth_state", self.client.session)
        self.assertEqual(self.client.session.get("google_oauth_next"), "/dashboard/")

    @override_settings(GOOGLE_CLIENT_ID="mock-client-id", GOOGLE_CLIENT_SECRET="mock-client-secret")
    def test_google_callback_rejects_invalid_state(self):
        session = self.client.session
        session["google_oauth_state"] = "valid-state"
        session.save()

        response = self.client.get(reverse("google_callback") + "?code=test-code&state=wrong-state")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("login"))

    @override_settings(GOOGLE_CLIENT_ID="mock-client-id", GOOGLE_CLIENT_SECRET="mock-client-secret")
    def test_google_callback_logs_in_existing_user(self):
        session = self.client.session
        session["google_oauth_state"] = "valid-state"
        session["google_oauth_next"] = "/dashboard/"
        session.save()

        token_mock = MagicMock()
        token_mock.read.return_value = json.dumps({"access_token": "mock-token"}).encode("utf-8")
        token_mock.__enter__.return_value = token_mock

        userinfo_mock = MagicMock()
        userinfo_mock.read.return_value = json.dumps({
            "email": "mohdfaizanali038@gmail.com",
            "email_verified": True,
            "name": "Faizan Ali",
            "given_name": "Faizan",
            "family_name": "Ali",
        }).encode("utf-8")
        userinfo_mock.__enter__.return_value = userinfo_mock

        with patch("urllib.request.urlopen", side_effect=[token_mock, userinfo_mock]):
            response = self.client.get(reverse("google_callback") + "?code=mock-code&state=valid-state")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, "/dashboard/")

            # Confirm user is logged in
            self.assertEqual(int(self.client.session["_auth_user_id"]), self.owner.id)

    @override_settings(GOOGLE_CLIENT_ID="mock-client-id", GOOGLE_CLIENT_SECRET="mock-client-secret")
    def test_google_callback_creates_new_candidate(self):
        session = self.client.session
        session["google_oauth_state"] = "valid-state"
        session["google_oauth_account_type"] = "student"
        session.save()

        token_mock = MagicMock()
        token_mock.read.return_value = json.dumps({"access_token": "mock-token"}).encode("utf-8")
        token_mock.__enter__.return_value = token_mock

        userinfo_mock = MagicMock()
        userinfo_mock.read.return_value = json.dumps({
            "email": "newstudent@example.com",
            "email_verified": True,
            "name": "Jane Student",
            "given_name": "Jane",
            "family_name": "Student",
        }).encode("utf-8")
        userinfo_mock.__enter__.return_value = userinfo_mock

        with patch("urllib.request.urlopen", side_effect=[token_mock, userinfo_mock]):
            response = self.client.get(reverse("google_callback") + "?code=mock-code&state=valid-state")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse("dashboard"))

            new_user = User.objects.get(email="newstudent@example.com")
            self.assertTrue(new_user.email_verified)
            self.assertEqual(new_user.account_type, User.AccountType.STUDENT)
            self.assertFalse(new_user.is_staff)
            self.assertFalse(new_user.has_usable_password())
            self.assertEqual(int(self.client.session["_auth_user_id"]), new_user.id)
