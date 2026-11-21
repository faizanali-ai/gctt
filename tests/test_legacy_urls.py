from datetime import date
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

LEGACY_WITHDRAW = "withdraw_application_legacy"


class LegacyUrlSunsetTests(TestCase):
    def test_headers_advertise_deprecation_before_sunset(self):
        with patch("config.middleware.SUNSET_DATE", date(2099, 1, 1)):
            response = self.client.post(reverse(LEGACY_WITHDRAW, args=[1]))
        self.assertEqual(response.headers["Deprecation"], "true")
        self.assertEqual(response.headers["Sunset"], "Fri, 19 Feb 2027 00:00:00 GMT")

    def test_legacy_routes_return_gone_after_sunset(self):
        with patch("config.middleware.SUNSET_DATE", date(2020, 1, 1)):
            response = self.client.post(reverse(LEGACY_WITHDRAW, args=[1]))
        self.assertEqual(response.status_code, 410)
        self.assertNotIn("Deprecation", response.headers)

    def test_non_legacy_routes_are_unaffected(self):
        response = self.client.get(reverse("healthz"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Deprecation", response.headers)
        self.assertNotIn("Sunset", response.headers)


class CheckLegacyUrlsCommandTests(TestCase):
    def test_reports_routes_before_sunset(self):
        call_command("check_legacy_urls", date="2026-11-21")

    def test_fails_after_sunset(self):
        with self.assertRaises(CommandError):
            call_command("check_legacy_urls", date="2030-01-01")
