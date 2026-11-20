from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from django_ratelimit.decorators import ratelimit

from . import views

password_reset_view = ratelimit(key="ip", rate="5/m", method="POST", block=True)(
    auth_views.PasswordResetView.as_view(
        template_name="accounts/password_reset.html",
        email_template_name="accounts/password_reset_email.txt",
        extra_email_context={"domain": "gctekton.com", "protocol": "https", "site_name": "GCTT"},
        success_url=reverse_lazy("password_reset_done"),
    )
)

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_view, name="login"),
    path("login/email/", views.email_otp_request, name="email_otp_request"),
    path("login/email/verify/", views.email_otp_verify, name="email_otp_verify"),
    path("login/email/resend/", views.email_otp_resend, name="email_otp_resend"),
    path("login/2fa/", views.legacy_2fa_redirect, name="login_2fa"),
    path("login/2fa/enroll/", views.legacy_2fa_redirect, name="login_2fa_enroll"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("google/login/", views.google_login, name="google_login"),
    path("google/callback/", views.google_callback, name="google_callback"),
    path("verify/<uidb64>/<token>/", views.verify_email, name="verify_email"),
    path("verify/resend/", views.resend_verification, name="resend_verification"),
    path("security/", views.security, name="security"),
    path("delete/", views.account_delete, name="account_delete"),
    path(
        "password-change/",
        auth_views.PasswordChangeView.as_view(
            template_name="accounts/password_change.html",
            success_url=reverse_lazy("profile"),
        ),
        name="password_change",
    ),
    path("password-reset/", password_reset_view, name="password_reset"),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path(
        "password-reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url=reverse_lazy("password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
]
