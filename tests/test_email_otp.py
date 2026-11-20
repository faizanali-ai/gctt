from datetime import timedelta
from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.email_otp import issue_code, purge_expired, verify_code
from apps.accounts.models import EmailOTP


class EmailOTPTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_code_is_hashed_and_single_use(self):
        otp, code = issue_code("User@Example.com")
        self.assertEqual(otp.email, "user@example.com")
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
        self.assertNotIn(code, otp.code_hash)
        self.assertTrue(verify_code("user@example.com", code))
        otp.refresh_from_db()
        self.assertIsNotNone(otp.consumed_at)
        self.assertFalse(verify_code("user@example.com", code))

    @override_settings(EMAIL_OTP_MAX_ATTEMPTS=3)
    def test_wrong_code_increments_attempts_and_locks(self):
        otp, code = issue_code("user@example.com")
        for _ in range(3):
            self.assertFalse(verify_code("user@example.com", "000000"))
        otp.refresh_from_db()
        self.assertEqual(otp.attempts, 3)
        self.assertIsNotNone(otp.consumed_at)
        self.assertFalse(verify_code("user@example.com", code))

    def test_expired_code_fails(self):
        otp, code = issue_code("user@example.com")
        otp.expires_at = timezone.now() - timedelta(minutes=1)
        otp.save(update_fields=["expires_at"])
        self.assertFalse(verify_code("user@example.com", code))

    def test_new_code_invalidates_previous(self):
        _, first_code = issue_code("user@example.com")
        cache.clear()
        _, second_code = issue_code("user@example.com")
        self.assertFalse(verify_code("user@example.com", first_code))
        self.assertTrue(verify_code("user@example.com", second_code))

    def test_resend_cooldown(self):
        self.assertIsNotNone(issue_code("user@example.com"))
        self.assertIsNone(issue_code("user@example.com"))
        cache.clear()
        self.assertIsNotNone(issue_code("user@example.com"))

    def test_purge_expired_removes_expired_and_consumed(self):
        expired, _ = issue_code("expired@example.com")
        expired.expires_at = timezone.now() - timedelta(minutes=1)
        expired.save(update_fields=["expires_at"])
        _, code = issue_code("used@example.com")
        self.assertTrue(verify_code("used@example.com", code))
        self.assertEqual(purge_expired(), 2)
        self.assertEqual(EmailOTP.objects.count(), 0)

    def test_purge_email_otp_command(self):
        expired, _ = issue_code("expired.command@example.com")
        expired.expires_at = timezone.now() - timedelta(minutes=1)
        expired.save(update_fields=["expires_at"])
        _, code = issue_code("used.command@example.com")
        self.assertTrue(verify_code("used.command@example.com", code))

        output = StringIO()
        call_command("purge_email_otp", stdout=output)
        self.assertIn("Purged 2 email OTP row(s).", output.getvalue())
        self.assertEqual(EmailOTP.objects.count(), 0)

    def test_unknown_email_and_empty_input_fail(self):
        self.assertFalse(verify_code("nobody@example.com", "000000"))
        self.assertIsNone(issue_code(""))
