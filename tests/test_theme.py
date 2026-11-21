from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User

STATIC = Path(settings.BASE_DIR) / "static"


class ThemeShellTests(TestCase):
    def test_theme_script_runs_before_stylesheet(self):
        html = self.client.get(reverse("home")).content.decode()
        self.assertLess(html.index("js/theme-init.js"), html.index("css/output.css"))
        self.assertIn('data-theme-toggle', html)

    def test_toggle_appears_on_auth_and_portal_pages(self):
        self.assertIn("data-theme-toggle", self.client.get(reverse("login")).content.decode())

        user = User.objects.create_user(
            email="candidate@example.com", password="test-pass-12345"
        )
        self.client.force_login(user)
        self.assertIn(
            "data-theme-toggle", self.client.get(reverse("dashboard")).content.decode()
        )

    def test_admin_site_is_removed(self):
        self.assertEqual(self.client.get("/admin/login/").status_code, 404)

    def test_theme_assets_exist(self):
        script = (STATIC / "js" / "theme-init.js").read_text(encoding="utf-8")
        self.assertIn("gctt-theme", script)
        self.assertIn("data-theme", script)
        app_js = (STATIC / "js" / "ui.js").read_text(encoding="utf-8")
        self.assertIn('THEME_KEY = "gctt-theme"', app_js)
        css = (STATIC / "css" / "input.css").read_text(encoding="utf-8")
        self.assertIn(':root[data-theme="dark"]', css)
        self.assertIn("@media (prefers-color-scheme: dark)", css)
