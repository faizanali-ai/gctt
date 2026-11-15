from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.accounts import views as accounts_views
from apps.jobs import views as jobs_views
from apps.training import views as training_views

from . import views

urlpatterns = [
    path("", views.page, {"template": "home"}, name="home"),
    path("about/", views.page, {"template": "about"}, name="about"),
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
    path("enquiries/", include("apps.enquiries.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("dashboard/", accounts_views.dashboard, name="dashboard"),
    path("dashboard/jobs/new/", jobs_views.job_create, name="employer_job_new"),
    path("dashboard/jobs/<slug:slug>/edit/", jobs_views.job_edit, name="employer_job_edit"),
    path(
        "dashboard/applications/<int:pk>/status/",
        jobs_views.application_status,
        name="employer_application_status",
    ),
    path("profile/", accounts_views.profile_edit, name="profile"),
    path("admin/", admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
