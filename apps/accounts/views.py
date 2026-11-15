from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django_ratelimit.decorators import ratelimit

from apps.enquiries.models import Enquiry
from apps.jobs.models import Application, Job
from apps.training.models import Programme, Registration

from .forms import ProfileForm, SignupForm


def signup(request):
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome to GCTT.")
        return redirect("dashboard")
    return render(request, "accounts/signup.html", {"form": form})


@ratelimit(key="ip", rate="10/m", method="POST", block=True)
def login_view(request, *args, **kwargs):
    return LoginView.as_view(template_name="accounts/login.html")(request, *args, **kwargs)


@login_required
def dashboard(request):
    if request.user.is_staff:
        return _staff_dashboard(request)
    return render(
        request,
        "accounts/dashboard.html",
        {
            "applications": request.user.applications.select_related("job"),
            "registrations": request.user.registrations.select_related("programme"),
        },
    )


def _staff_dashboard(request):
    user = request.user
    sections = []

    def add(label, url_name, perm, count, note=""):
        if user.has_perm(perm):
            sections.append({"label": label, "url": url_name, "count": count, "note": note})

    add("Enquiries", "staff_enquiries", "enquiries.view_enquiry",
        Enquiry.objects.filter(status=Enquiry.Status.NEW).count(), "new")
    add("Jobs", "staff_jobs", "jobs.view_job",
        Job.objects.count(), f"{Job.objects.filter(published=False).count()} awaiting review")
    add("Applications", "staff_applications", "jobs.view_application",
        Application.objects.count())
    add("Programmes", "staff_programmes", "training.view_programme",
        Programme.objects.count(), f"{Programme.objects.filter(published=False).count()} drafts")
    add("Registrations", "staff_registrations", "training.view_registration",
        Registration.objects.count())

    return render(
        request,
        "accounts/staff_dashboard.html",
        {
            "sections": sections,
            "is_ceo": user.is_superuser,
            "can_use_admin": user.is_superuser or user.has_perm("jobs.delete_job"),
        },
    )


@login_required
def profile_edit(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile saved.")
        return redirect("profile")
    return render(request, "accounts/profile_edit.html", {"form": form})
