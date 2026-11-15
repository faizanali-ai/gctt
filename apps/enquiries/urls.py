from django.urls import path

from . import views

urlpatterns = [
    path("submit/", views.submit_enquiry, name="submit_enquiry"),
]
