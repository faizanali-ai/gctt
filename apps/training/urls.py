from django.urls import path

from . import views

urlpatterns = [
    path("", views.programme_list, name="training"),
    path("<slug:slug>/", views.programme_detail, name="programme_detail"),
    path("<slug:slug>/register/", views.programme_register, name="programme_register"),
]
