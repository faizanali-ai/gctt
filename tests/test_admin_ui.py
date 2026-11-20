from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AdminShellTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser(
            email="admin-ui@example.com",
            password="test-pass-12345",
        )

    def test_login_page_uses_branded_shell(self):
        response = self.client.get(reverse("admin:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "GCTT Administration")
        self.assertContains(response, "admin-brand")

    def test_index_uses_branded_shell(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "GCTT Administration")
        self.assertContains(response, "Public site")
        self.assertContains(response, "admin-brand")

    def test_changelist_uses_branded_shell(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin:jobs_job_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "GCTT Administration")
