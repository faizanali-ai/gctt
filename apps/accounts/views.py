from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django_ratelimit.decorators import ratelimit

from apps.enquiries.models import Enquiry
from apps.jobs.models import Application, Job
from apps.training.models import Registration

from .forms import ProfileForm, SignupForm

User = get_user_model()


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
    if request.user.is_employer:
        from apps.jobs.views import employer_dashboard

        return employer_dashboard(request)
    return render(
        request,
        "accounts/dashboard.html",
        {
            "applications": request.user.applications.select_related("job"),
            "registrations": request.user.registrations.select_related("programme"),
        },
    )


def _staff_dashboard(request):
    return render(
        request,
        "accounts/staff_dashboard.html",
        {
            "counts": {
                "candidates": User.objects.filter(account_type=User.AccountType.CANDIDATE).count(),
                "students": User.objects.filter(account_type=User.AccountType.STUDENT).count(),
                "employers": User.objects.filter(account_type=User.AccountType.EMPLOYER).count(),
                "jobs": Job.objects.filter(published=True).count(),
                "drafts": Job.objects.filter(published=False).count(),
                "applications": Application.objects.count(),
                "registrations": Registration.objects.count(),
                "new_enquiries": Enquiry.objects.filter(status=Enquiry.Status.NEW).count(),
            },
            "latest_enquiries": Enquiry.objects.all()[:5],
            "latest_applications": Application.objects.select_related("job", "applicant")[:5],
            "latest_registrations": Registration.objects.select_related("programme", "student")[:5],
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
