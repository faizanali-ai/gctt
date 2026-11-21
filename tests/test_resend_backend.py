import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives
from django.test import SimpleTestCase, override_settings

from config.email_backends import ResendEmailBackend


def fake_response():
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = b'{"id":"email_123"}'
    return response


@override_settings(
    RESEND_API_KEY="re_test_key",
    DEFAULT_FROM_EMAIL="accounts@example.com",
    EMAIL_TIMEOUT=5,
)
class ResendBackendTests(SimpleTestCase):
    def test_sends_text_html_and_headers(self):
        message = EmailMultiAlternatives(
            "Sign-in code",
            "Your code is 123456",
            "accounts@example.com",
            ["user@example.com"],
            headers={"List-Unsubscribe": "<https://example.com/unsubscribe/>"},
        )
        message.attach_alternative("<p>Your code is <strong>123456</strong></p>", "text/html")
        message.idempotency_key = "test-idempotency-key"

        with patch("urllib.request.urlopen", return_value=fake_response()) as urlopen:
            self.assertEqual(ResendEmailBackend().send_messages([message]), 1)

        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request.full_url, "https://api.resend.com/emails")
        self.assertEqual(request.headers["Authorization"], "Bearer re_test_key")
        self.assertIn("GCTT-Mailer/", request.headers["User-agent"])
        self.assertEqual(request.headers["Idempotency-key"], "test-idempotency-key")
        self.assertEqual(payload["from"], "accounts@example.com")
        self.assertEqual(payload["to"], ["user@example.com"])
        self.assertEqual(payload["subject"], "Sign-in code")
        self.assertEqual(payload["text"], "Your code is 123456")
        self.assertIn("<strong>123456</strong>", payload["html"])
        self.assertEqual(
            payload["headers"]["List-Unsubscribe"],
            "<https://example.com/unsubscribe/>",
        )

    def test_http_error_is_raised(self):
        message = EmailMultiAlternatives(
            "Subject", "Body", "accounts@example.com", ["user@example.com"]
        )
        error = urllib.error.HTTPError(
            "https://api.resend.com/emails",
            500,
            "server error",
            {},
            io.BytesIO(b'{"message":"nope"}'),
        )
        with (
            patch("urllib.request.urlopen", side_effect=error),
            self.assertRaises(RuntimeError),
        ):
            ResendEmailBackend().send_messages([message])

    @override_settings(RESEND_API_KEY="")
    def test_missing_api_key_is_rejected(self):
        message = EmailMultiAlternatives(
            "Subject", "Body", "accounts@example.com", ["user@example.com"]
        )
        with self.assertRaises(ImproperlyConfigured):
            ResendEmailBackend().send_messages([message])
