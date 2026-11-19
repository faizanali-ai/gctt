from django.contrib import admin as django_admin
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts.admin import UserAdmin
from apps.accounts.apps import assign_permissions
from apps.accounts.models import User
from apps.training.models import Programme, Registration


def make_user(email, **extra):
    return User.objects.create_user(email=email, password="test-pass-12345", **extra)


def current_token(device):
    return f"{totp(device.bin_key, step=device.step, t0=device.t0, digits=device.digits):06d}"


@override_settings(REQUIRE_STAFF_2FA=True)
class EnforcedStaffTwoFactorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()
        cls.trainer = make_user(
            "audit.trainer@example.com", role=User.Role.STAFF, is_staff=True
        )
        cls.trainer.groups.add(Group.objects.get(name="Trainer"))
        cls.student = make_user(
            "audit.student@example.com", account_type=User.AccountType.STUDENT
        )
        programme = Programme.objects.create(
            title="Audit Programme", description="x", published=True
        )
        cls.registration = Registration.objects.create(
            programme=programme, student=cls.student, status=Registration.Status.COMPLETED
        )
        cls.registration.issue_certificate()

    def test_admin_login_redirects_before_creating_session(self):
        response = self.client.post(
            reverse("admin:login"),
            {
                "username": self.trainer.email,
                "password": "test-pass-12345",
                "next": "/admin/",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_unverified_staff_cannot_download_certificate(self):
        self.client.force_login(self.trainer)
        response = self.client.get(
            reverse("download_certificate", args=[self.registration.certificate_ref])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("security"), response.url)

    def test_unenrolled_staff_gets_no_full_session(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.trainer.email, "password": "test-pass-12345"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("login_2fa"))
        self.assertNotIn("_auth_user_id", self.client.session)

        response = self.client.get(reverse("login_2fa"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("login_2fa_enroll"))

        response = self.client.post(reverse("account_delete"), {})
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

        self.client.force_login(self.trainer)
        for path in (reverse("account_delete"), reverse("password_change")):
            response = self.client.post(path, {})
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("security"), response.url)

    def test_enrollment_logs_in_only_after_valid_token(self):
        self.client.post(
            reverse("login"),
            {"username": self.trainer.email, "password": "test-pass-12345"},
        )
        response = self.client.get(reverse("login_2fa_enroll"))
        self.assertEqual(response.status_code, 200)

        device = TOTPDevice.objects.get(user=self.trainer, confirmed=False)
        response = self.client.post(
            reverse("login_2fa_enroll"), {"token": current_token(device)}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)
        device.refresh_from_db()
        self.assertTrue(device.confirmed)

    def test_disable_requires_current_totp_code(self):
        device = TOTPDevice.objects.create(
            user=self.trainer, name="primary", confirmed=True
        )
        self.client.force_login(self.trainer)

        # Unverified sessions cannot disable 2FA even with a valid code.
        self.client.post(
            reverse("security"),
            {
                "action": "disable",
                "password": "test-pass-12345",
                "token": current_token(device),
            },
        )
        self.assertEqual(TOTPDevice.objects.filter(user=self.trainer).count(), 1)

        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = device.persistent_id
        session.save()

        self.client.post(
            reverse("security"),
            {
                "action": "disable",
                "password": "test-pass-12345",
                "token": "not-a-code",
            },
        )
        self.assertEqual(TOTPDevice.objects.filter(user=self.trainer).count(), 1)

        # Clear django-otp's one-second failure throttle for the next attempt.
        device.refresh_from_db()
        device.throttling_failure_count = 0
        device.throttling_failure_timestamp = None
        device.save(update_fields=["throttling_failure_count", "throttling_failure_timestamp"])

        self.client.post(
            reverse("security"),
            {
                "action": "disable",
                "password": "test-pass-12345",
                "token": current_token(device),
            },
        )
        self.assertEqual(TOTPDevice.objects.filter(user=self.trainer).count(), 0)


class StaffAccessControlTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()

    def test_leftover_direct_permission_does_not_grant_staff_portal(self):
        user = make_user("leftover@example.com", account_type=User.AccountType.CANDIDATE)
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
