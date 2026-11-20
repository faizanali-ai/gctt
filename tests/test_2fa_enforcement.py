from django.contrib import admin as django_admin
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.accounts.admin import UserAdmin
from apps.accounts.apps import assign_permissions
from apps.accounts.models import User


@override_settings(
    REQUIRE_EMAIL_OTP=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class EmailOTPEnforcementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()
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

    def login(self, email):
        return self.client.post(
            reverse("login"),
            {"username": email, "password": "test-pass-12345"},
        )

    def test_staff_login_requires_email_otp(self):
        response = self.login(self.staff.email)
        self.assertRedirects(response, reverse("email_otp_verify"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_admin_login_requires_email_otp(self):
        response = self.login(self.admin.email)
        self.assertRedirects(response, reverse("email_otp_verify"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_admin_can_access_admin_without_totp(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_candidate_password_login_is_unchanged(self):
        response = self.login(self.candidate.email)
        self.assertRedirects(response, reverse("dashboard"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_old_2fa_routes_redirect_to_login(self):
        self.assertRedirects(
            self.client.get(reverse("login_2fa")), reverse("login")
        )
        self.assertRedirects(
            self.client.get(reverse("login_2fa_enroll")), reverse("login")
        )


class StaffAccessControlTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()

    def test_leftover_direct_permission_does_not_grant_staff_portal(self):
        user = User.objects.create_user(
            email="leftover@example.com", account_type=User.AccountType.CANDIDATE
        )
        user.is_staff = False
        user.save(update_fields=["is_staff"])
        user.user_permissions.add(
            Permission.objects.get(codename="view_application")
        )
        self.client.force_login(user)
        response = self.client.get(reverse("staff_applications"))
        self.assertEqual(response.status_code, 403)

    def test_non_integer_filter_params_do_not_crash(self):
        admin = User.objects.create_superuser(
            email="filters@example.com", password="test-pass-12345"
        )
        self.client.force_login(admin)
        self.assertEqual(
            self.client.get(reverse("staff_applications"), {"job": "abc"}).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse("staff_registrations"), {"programme": "abc"}
            ).status_code,
            200,
        )


class UserAdminGuardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin.guard@example.com", password="test-pass-12345"
        )
        self.model_admin = UserAdmin(User, django_admin.site)
        self.request = RequestFactory().post("/admin/accounts/user/")
        self.request.user = self.admin

    def test_self_demotion_is_blocked(self):
        self.admin.role = User.Role.STAFF
        with self.assertRaises(PermissionDenied):
            self.model_admin.save_model(self.request, self.admin, None, True)

    def test_self_delete_is_hidden_and_bulk_delete_is_disabled(self):
        self.assertFalse(self.model_admin.has_delete_permission(self.request, self.admin))
        self.assertNotIn("delete_selected", self.model_admin.get_actions(self.request))
