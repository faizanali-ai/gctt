from django.urls import path

from . import views

urlpatterns = [
    path("", views.programme_list, name="training"),
    path("verify/", views.verify_certificate, name="verify_certificate_form"),
    path("verify/<str:ref>/", views.verify_certificate, name="verify_certificate"),
    path("certificate/<str:ref>/", views.download_certificate, name="download_certificate"),
    path("<slug:slug>/", views.programme_detail, name="programme_detail"),
    path("<slug:slug>/register/", views.programme_register, name="programme_register"),
]
