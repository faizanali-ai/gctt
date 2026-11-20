from urllib.parse import urlencode

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.shortcuts import redirect
from django.urls import include, path, reverse
from django.views.generic import TemplateView
from django_ratelimit.decorators import ratelimit

from apps.accounts import views as accounts_views
from apps.enquiries import views as enquiries_views
from apps.jobs import views as jobs_views
from apps.training import views as training_views

from . import views
from .sitemaps import JobSitemap, ProgrammeSitemap, StaticSitemap

admin.site.site_header = "GCTT Administration"
admin.site.site_title = "GCTT Admin"
admin.site.index_title = "Operations"

# Admin accounts sign in with email OTP only; never mint a password session.
@ratelimit(key="ip", rate="10/m", method="POST", block=True)
def _admin_login_guard(request, extra_context=None):
    if request.user.is_authenticated and getattr(request.user, "is_admin", False):
        return redirect("/admin/")
    target = request.GET.get("next") or request.POST.get("next") or "/admin/"
    return redirect(
        f"{reverse('email_otp_request')}?{urlencode({'next': target})}"
    )


admin.site.login = _admin_login_guard

sitemaps = {
    "static": StaticSitemap,
    "jobs": JobSitemap,
    "programmes": ProgrammeSitemap,
}

urlpatterns = [
    path("", views.page, {"template": "home"}, name="home"),
    path("about/", views.about, name="about"),
    path("services/", views.page, {"template": "services"}, name="services"),
    path("it-staffing/", views.page, {"template": "it_staffing"}, name="it_staffing"),
    path("recruitment/", views.page, {"template": "recruitment"}, name="recruitment"),
    path(
        "talent-acquisition/",
        views.page,
        {"template": "talent_acquisition"},
        name="talent_acquisition",
    ),
    path("sap-scrum/", training_views.sap_scrum, name="sap_scrum"),
    path(
        "career-restart/",
        views.page,
        {"template": "career_restart"},
        name="career_restart",
    ),
    path("employers/", views.page, {"template": "employers"}, name="employers"),
    path("contact/", views.page, {"template": "contact"}, name="contact"),
    path("privacy/", views.page, {"template": "privacy"}, name="privacy"),
    path("terms/", views.page, {"template": "terms"}, name="terms"),
    path("careers/", include("apps.jobs.urls")),
    path("training/", include("apps.training.urls")),
    path("api/career-advisor/", training_views.api_career_advisor, name="api_career_advisor_alias"),
    path("enquiries/", include("apps.enquiries.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("dashboard/", accounts_views.dashboard, name="dashboard"),
    path(
        "dashboard/applications/<uuid:uuid>/withdraw/",
        jobs_views.withdraw_application,
        name="withdraw_application",
    ),
    path(
        "dashboard/applications/<int:pk>/withdraw/",
        jobs_views.withdraw_application,
        name="withdraw_application_legacy",
    ),
    path("profile/", accounts_views.profile_edit, name="profile"),
    path("manage/users/", accounts_views.manage_users, name="manage_users"),
    path("manage/users/new/", accounts_views.manage_user_create, name="manage_user_create"),
    path("manage/users/<int:pk>/", accounts_views.manage_user_edit, name="manage_user_edit"),
    path("manage/users/<int:pk>/delete/", accounts_views.manage_user_delete, name="manage_user_delete"),
    path("staff/enquiries/", enquiries_views.staff_enquiries, name="staff_enquiries"),
    path(
        "staff/enquiries/<int:pk>/status/",
        enquiries_views.staff_enquiry_status,
        name="staff_enquiry_status",
    ),
    path("staff/jobs/", jobs_views.staff_jobs, name="staff_jobs"),
    path(
        "staff/jobs/<int:pk>/publish/",
        jobs_views.staff_job_publish,
        name="staff_job_publish",
    ),
    path(
        "staff/jobs/<int:pk>/linkedin/",
        jobs_views.staff_job_linkedin_post,
        name="staff_job_linkedin_post",
    ),
    path("staff/applications/", jobs_views.staff_applications, name="staff_applications"),
    path(
        "staff/applications/<uuid:uuid>/status/",
        jobs_views.staff_application_status,
        name="staff_application_status",
    ),
    path(
        "staff/applications/<int:pk>/status/",
        jobs_views.staff_application_status,
        name="staff_application_status_legacy",
    ),
    path("staff/programmes/", training_views.staff_programmes, name="staff_programmes"),
    path(
        "staff/programmes/<int:pk>/toggle/",
        training_views.staff_programme_toggle,
        name="staff_programme_toggle",
    ),
    path(
        "staff/registrations/", training_views.staff_registrations, name="staff_registrations"
    ),
    path(
        "staff/registrations/<uuid:uuid>/status/",
        training_views.staff_registration_status,
        name="staff_registration_status",
    ),
    path(
        "staff/registrations/<int:pk>/status/",
        training_views.staff_registration_status,
        name="staff_registration_status_legacy",
    ),
    path(
        "staff/registrations/<uuid:uuid>/certificate/",
        training_views.staff_registration_certificate,
        name="staff_registration_certificate",
    ),
    path(
        "staff/registrations/<int:pk>/certificate/",
        training_views.staff_registration_certificate,
        name="staff_registration_certificate_legacy",
    ),
    path("admin/", admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("healthz/", views.healthz, name="healthz"),
    path("health/", views.healthz),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        name="robots",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
