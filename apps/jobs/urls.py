from django.urls import path

from . import views

urlpatterns = [
    path("", views.job_list, name="careers"),
    path("<slug:slug>/", views.job_detail, name="job_detail"),
    path("<slug:slug>/apply/", views.job_apply, name="job_apply"),
]
