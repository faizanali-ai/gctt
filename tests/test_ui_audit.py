from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.training.models import Category, Programme


class HubNavigationTests(TestCase):
    def test_solutions_hub_subnav_marks_the_active_section(self):
        response = self.client.get(reverse("services"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Talent Solutions sections"')
        self.assertContains(response, 'aria-current="page"')

    def test_child_page_marks_its_own_subnav_link(self):
        response = self.client.get(reverse("it_staffing"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "IT Staffing")

    def test_academy_hub_has_subnav(self):
        response = self.client.get(reverse("training"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Academy sections"')


class RegistrationFeedbackTests(TestCase):
    def test_invalid_guest_registration_is_not_silent(self):
        category = Category.objects.create(name="Test Track", published=True)
        programme = Programme.objects.create(
            title="Test Programme",
            category=category,
            published=True,
            registration_open=True,
        )
        response = self.client.post(
            reverse("programme_register", args=[programme.slug]),
            {"full_name": "", "email": "typed@example.com", "message": ""},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please correct the following")
        self.assertContains(response, "This field is required.")
        self.assertContains(response, 'value="typed@example.com"')

    def test_authenticated_staff_see_no_student_registration_form(self):
        category = Category.objects.create(name="Test Track", published=True)
        programme = Programme.objects.create(
            title="Test Programme",
            category=category,
            published=True,
            registration_open=True,
        )
        staff = get_user_model().objects.create_user(
            email="staff-audit@example.com",
            password="test-pass-12345",
            role="staff",
            is_staff=True,
        )
        self.client.force_login(staff)
        response = self.client.get(reverse("programme_detail", args=[programme.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student account required")


class UserFormValueTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser(
            email="ui-audit-admin@example.com",
            password="test-pass-12345",
        )

    def test_invalid_user_create_keeps_typed_values(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("manage_user_create"),
            {
                "email": "typed@example.com",
                "first_name": "Typed",
                "last_name": "Person",
                "role": "staff",
                "group": "Recruiter",
                "password": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="typed@example.com"')
        self.assertContains(response, 'value="Typed"')
        self.assertContains(response, "data-form-errors")

    def test_create_form_defaults_to_staff_role(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("manage_user_create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="staff" selected')
        self.assertNotContains(response, 'value="admin" selected')
