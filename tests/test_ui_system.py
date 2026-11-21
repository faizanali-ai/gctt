import re
from pathlib import Path

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
COMPILED_CSS = Path(__file__).resolve().parent.parent / "static" / "css" / "output.css"
SOURCE_CSS = Path(__file__).resolve().parent.parent / "static" / "css" / "input.css"
IMAGES = Path(__file__).resolve().parent.parent / "static" / "images"
FONTS = Path(__file__).resolve().parent.parent / "static" / "fonts"

# HTML email clients require inline colours; the web token guard does not apply.
EXCLUDED_DIRS = {TEMPLATES / "emails"}


def template_files():
    for path in TEMPLATES.rglob("*.html"):
        if any(path.is_relative_to(excluded) for excluded in EXCLUDED_DIRS):
            continue
        yield path


class TemplateGuardTests(SimpleTestCase):
    def test_no_hardcoded_hex_colours(self):
        offenders = []
        for path in template_files():
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"#[0-9a-fA-F]{6}", line):
                    offenders.append(f"{path.name}:{number}")
        self.assertEqual(offenders, [], "Hardcoded colours in templates")

    def test_no_legacy_font_code(self):
        legacy = ("fonts.googleapis",)
        for path in template_files():
            text = path.read_text(encoding="utf-8")
            for token in legacy:
                self.assertNotIn(token, text, f"{token} in {path.name}")

    def test_no_native_dialogs_or_inline_handlers(self):
        for path in template_files():
            text = path.read_text(encoding="utf-8")
            for token in ("alert(", "confirm(", "onclick=", "onsubmit="):
                self.assertNotIn(token, text, f"{token} in {path.name}")

    def test_only_json_ld_scripts_are_inline(self):
        for path in template_files():
            for match in re.finditer(r"<script\b([^>]*)>", path.read_text(encoding="utf-8")):
                attrs = match.group(1)
                if "src=" in attrs:
                    continue
                self.assertIn("application/ld+json", attrs, f"inline script in {path.name}")

    def test_no_legacy_component_classes(self):
        legacy = (
            "btn-stitch",
            "stitch-card",
            "btn-brutal",
            "glass-card",
            "text-ink-muted",
            "text-ink-subtle",
            "border-line-subtle",
            "font-serif",
        )
        for path in template_files():
            text = path.read_text(encoding="utf-8")
            for token in legacy:
                self.assertNotIn(token, text, f"{token} in {path.name}")


class CompiledCSSGuardTests(SimpleTestCase):
    def test_theme_layer_uses_runtime_tokens(self):
        source = SOURCE_CSS.read_text(encoding="utf-8")
        self.assertIn("@theme inline", source)
        self.assertIn(':root[data-theme="dark"]', source)
        self.assertIn("@custom-variant dark", source)

    def test_required_utilities_are_compiled(self):
        css = COMPILED_CSS.read_text(encoding="utf-8")
        for utility in (
            "bg-canvas",
            "bg-surface",
            "bg-raised",
            "text-ink",
            "text-muted",
            "border-line",
            "text-accent",
            "bg-accent-soft",
            "bg-night",
            "text-night-ink",
            "text-night-accent",
            "text-2xs",
            "text-3xs",
        ):
            self.assertRegex(css, rf"\.{re.escape(utility)}\b", f"missing .{utility}")

    def test_motion_and_visual_components_are_compiled(self):
        css = COMPILED_CSS.read_text(encoding="utf-8")
        for component in (".hero-enter", ".hero-art", ".geometry"):
            self.assertIn(component, css, f"missing {component}")


class AssetBudgetTests(SimpleTestCase):
    def test_images_are_within_budget(self):
        for path in IMAGES.iterdir():
            if path.is_file():
                self.assertLessEqual(path.stat().st_size, 300 * 1024, f"{path.name} exceeds 300 KB")

    def test_fonts_are_within_budget(self):
        total = sum(path.stat().st_size for path in FONTS.glob("*.woff2"))
        self.assertLessEqual(total, 180 * 1024, "font payload exceeds 180 KB")

    def test_compiled_css_is_within_budget(self):
        self.assertLessEqual(COMPILED_CSS.stat().st_size, 65 * 1024, "CSS exceeds 65 KB")


class VisualStructureTests(SimpleTestCase):
    def test_home_hero_has_entrance_and_abstract_art(self):
        home = (TEMPLATES / "pages" / "home.html").read_text(encoding="utf-8")
        self.assertIn("hero-enter", home)
        self.assertIn("_hero-art.html", home)

    def test_inner_hero_uses_geometry(self):
        hero = (TEMPLATES / "partials" / "_hero.html").read_text(encoding="utf-8")
        self.assertIn("_geometry.html", hero)


class PublicPageTests(TestCase):
    def setUp(self):
        from config.site import clear_company_cache

        clear_company_cache()

    def test_marketing_pages_render_one_h1_with_shell(self):
        pages = [
            "home",
            "services",
            "it_staffing",
            "recruitment",
            "talent_acquisition",
            "sap_scrum",
            "employers",
            "about",
            "contact",
            "privacy",
            "terms",
            "careers",
            "training",
            "career_restart",
            "verify_certificate_form",
        ]
        for name in pages:
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                html = response.content.decode()
                self.assertEqual(html.count("<h1"), 1, f"h1 count on {name}")
                self.assertIn("Skip to content", html)
                self.assertIn('aria-label="GCTT home"', html)
                self.assertIn("Open mandates", html)

    def test_auth_pages_render_one_h1(self):
        for name in ("login", "signup", "password_reset"):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content.decode().count("<h1"), 1)

    def test_primary_navigation_has_five_divisions(self):
        response = self.client.get(reverse("home"))
        html = response.content.decode()
        for label in ("Talent Solutions", "Academy", "Careers", "Company", "Contact"):
            self.assertIn(label, html)

    def test_404_is_branded(self):
        response = self.client.get("/this-page-does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Page not found", status_code=404)
        self.assertContains(response, "Error 404", status_code=404)


class MetadataTests(TestCase):
    def test_auth_pages_are_not_indexed(self):
        for name in ("login", "signup", "password_reset"):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertContains(response, 'content="noindex"')

    def test_404_is_not_indexed(self):
        response = self.client.get("/this-page-does-not-exist/")
        self.assertContains(response, 'content="noindex"', status_code=404)

    def test_base_references_current_social_and_icon_assets(self):
        response = self.client.get(reverse("home"))
        html = response.content.decode()
        self.assertIn("images/og-gctt-v3.jpg", html)
        self.assertIn("images/logo-icon-512.png", html)
        self.assertNotIn("og-gctt-v2", html)
        self.assertNotIn("logo-small.webp", html)
        for name in ("og-gctt-v3.jpg", "logo-icon-512.png"):
            self.assertTrue((IMAGES / name).is_file(), f"missing {name}")


class DashboardLayoutTests(SimpleTestCase):
    def test_summary_grid_has_an_explicit_single_column(self):
        dashboard = (TEMPLATES / "accounts" / "staff_dashboard.html").read_text(encoding="utf-8")
        self.assertIn("grid grid-cols-1", dashboard)


class StickyTableTests(SimpleTestCase):
    def test_sticky_header_is_desktop_only(self):
        source = SOURCE_CSS.read_text(encoding="utf-8")
        self.assertRegex(
            source,
            r"@media \(min-width: 768px\) \{\s*\.data-table th \{\s*position: sticky;",
        )

    def test_staff_tables_have_a_bounded_scroll_area(self):
        for path in sorted((TEMPLATES / "staff").glob("*.html")):
            text = path.read_text(encoding="utf-8")
            if "data-table" not in text:
                continue
            self.assertIn("md:max-h-[70vh]", text, f"{path.name} needs a max height")
            self.assertIn("md:overflow-auto", text, f"{path.name} needs auto overflow")
