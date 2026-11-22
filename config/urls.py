
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import TemplateView

from apps.accounts import views as accounts_views
from apps.enquiries import views as enquiries_views
from apps.jobs import views as jobs_views
from apps.training import views as training_views

from . import views
from .sitemaps import JobSitemap, ProgrammeSitemap, StaticSitemap

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
    path("manage/team/", accounts_views.manage_team, name="manage_team"),
    path("manage/team/new/", accounts_views.manage_team_create, name="manage_team_create"),
    path("manage/team/<int:pk>/", accounts_views.manage_team_edit, name="manage_team_edit"),
    path("manage/team/<int:pk>/delete/", accounts_views.manage_team_delete, name="manage_team_delete"),
    path("manage/pages/", accounts_views.manage_pages, name="manage_pages"),
    path("manage/pages/<slug:page_slug>/", accounts_views.manage_page_edit, name="manage_page_edit"),
    path("manage/pages/<slug:page_slug>/faqs/new/", accounts_views.manage_faq_create, name="manage_faq_create"),
    path("manage/faqs/<int:pk>/edit/", accounts_views.manage_faq_edit, name="manage_faq_edit"),
    path("manage/faqs/<int:pk>/delete/", accounts_views.manage_faq_delete, name="manage_faq_delete"),
    path("manage/navigation/", accounts_views.manage_navigation, name="manage_navigation"),
    path("manage/navigation/<int:pk>/edit/", accounts_views.manage_navigation_edit, name="manage_navigation_edit"),
    path("manage/navigation/<int:pk>/delete/", accounts_views.manage_navigation_delete, name="manage_navigation_delete"),
    path("manage/media/", accounts_views.manage_media, name="manage_media"),
    path("manage/media/<int:pk>/delete/", accounts_views.manage_media_delete, name="manage_media_delete"),
    path("manage/settings/", accounts_views.manage_site_settings, name="manage_site_settings"),
    path("manage/audit/", accounts_views.manage_audit, name="manage_audit"),
    path("staff/enquiries/", enquiries_views.staff_enquiries, name="staff_enquiries"),
    path(
        "staff/enquiries/<int:pk>/",
        enquiries_views.staff_enquiry_edit,
        name="staff_enquiry_edit",
    ),
    path(
        "staff/enquiries/<int:pk>/delete/",
        enquiries_views.staff_enquiry_delete,
        name="staff_enquiry_delete",
    ),
    path(
        "staff/enquiries/<int:pk>/status/",
        enquiries_views.staff_enquiry_status,
        name="staff_enquiry_status",
    ),
    path("staff/jobs/", jobs_views.staff_jobs, name="staff_jobs"),
    path("staff/jobs/new/", jobs_views.staff_job_create, name="staff_job_create"),
    path(
        "staff/jobs/<int:pk>/edit/",
        jobs_views.staff_job_edit,
        name="staff_job_edit",
    ),
    path(
        "staff/jobs/<int:pk>/delete/",
        jobs_views.staff_job_delete,
        name="staff_job_delete",
    ),
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
        "staff/applications/bulk/",
        jobs_views.staff_applications_bulk,
        name="staff_applications_bulk",
    ),
    path(
        "staff/applications/<uuid:uuid>/",
        jobs_views.staff_application_edit,
        name="staff_application_edit",
    ),
    path(
        "staff/applications/<uuid:uuid>/delete/",
        jobs_views.staff_application_delete,
        name="staff_application_delete",
    ),
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
    path("staff/categories/", training_views.staff_categories, name="staff_categories"),
    path(
        "staff/categories/new/",
        training_views.staff_category_create,
        name="staff_category_create",
    ),
    path(
        "staff/categories/<int:pk>/edit/",
        training_views.staff_category_edit,
        name="staff_category_edit",
    ),
    path(
        "staff/categories/<int:pk>/delete/",
        training_views.staff_category_delete,
        name="staff_category_delete",
    ),
    path("staff/programmes/", training_views.staff_programmes, name="staff_programmes"),
    path(
        "staff/programmes/new/",
        training_views.staff_programme_create,
        name="staff_programme_create",
    ),
    path(
        "staff/programmes/<int:pk>/edit/",
        training_views.staff_programme_edit,
        name="staff_programme_edit",
    ),
    path(
        "staff/programmes/<int:pk>/delete/",
        training_views.staff_programme_delete,
        name="staff_programme_delete",
    ),
    path(
        "staff/programmes/<int:pk>/toggle/",
        training_views.staff_programme_toggle,
        name="staff_programme_toggle",
    ),
    path(
        "staff/registrations/", training_views.staff_registrations, name="staff_registrations"
    ),
    path(
        "staff/registrations/<uuid:uuid>/",
        training_views.staff_registration_edit,
        name="staff_registration_edit",
    ),
    path(
        "staff/registrations/<uuid:uuid>/delete/",
        training_views.staff_registration_delete,
        name="staff_registration_delete",
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
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("wake/", views.wake, name="wake"),
    path("healthz/", views.healthz, name="healthz"),
    path("health/", views.healthz),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        name="robots",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
