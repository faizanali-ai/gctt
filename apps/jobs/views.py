from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from apps.accounts.decorators import employer_required

from .forms import ApplicationForm, JobForm
from .models import Application, Job

EMPLOYER_STATUSES = {
    Application.Status.UNDER_REVIEW,
    Application.Status.SHORTLISTED,
    Application.Status.REJECTED,
    Application.Status.SELECTED,
}


def job_list(request):
    jobs = Job.objects.filter(published=True)
    q = request.GET.get("q", "").strip()
    if q:
        jobs = jobs.filter(
            Q(title__icontains=q) | Q(location__icontains=q) | Q(description__icontains=q)
        )
    return render(request, "jobs/job_list.html", {"jobs": jobs, "q": q})


def job_detail(request, slug):
    job = get_object_or_404(Job, slug=slug, published=True)
    applied = (
        request.user.is_authenticated
        and job.applications.filter(applicant=request.user).exists()
    )
    return render(
        request,
        "jobs/job_detail.html",
        {"job": job, "form": ApplicationForm(), "applied": applied},
    )


@require_POST
@login_required
@ratelimit(key="user", rate="20/h", method="POST", block=True)
def job_apply(request, slug):
    job = get_object_or_404(Job, slug=slug, published=True)
    if request.user.is_employer:
        messages.error(request, "Employer accounts can't apply to jobs.")
        return redirect("job_detail", slug=job.slug)
    form = ApplicationForm(request.POST, request.FILES)
    if form.is_valid():
        application = form.save(commit=False)
        application.job = job
        application.applicant = request.user
        try:
            with transaction.atomic():
                application.save()
            messages.success(request, "Your application has been sent.")
        except IntegrityError:
            messages.error(request, "You have already applied to this job.")
        return redirect("job_detail", slug=job.slug)
    return render(
        request,
        "jobs/job_detail.html",
        {"job": job, "form": form, "applied": False},
    )


@employer_required
def employer_dashboard(request):
    jobs = request.user.jobs.annotate(applications_count=Count("applications"))
    applications = Application.objects.filter(job__employer=request.user).select_related(
        "job", "applicant"
    )
    return render(
        request,
        "jobs/employer_dashboard.html",
        {
            "jobs": jobs,
            "live_count": jobs.filter(published=True).count(),
            "applications": applications,
            "statuses": [
                choice for choice in Application.Status.choices if choice[0] in EMPLOYER_STATUSES
            ],
        },
    )


@employer_required
def job_create(request):
    form = JobForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        job = form.save(commit=False)
        job.employer = request.user
        job.published = False
        job.save()
        messages.success(request, "Job submitted — our team reviews and publishes it.")
        return redirect("dashboard")
    return render(request, "jobs/employer_job_form.html", {"form": form, "job": None})


@employer_required
def job_edit(request, slug):
    job = get_object_or_404(Job, slug=slug, employer=request.user)
    form = JobForm(request.POST or None, instance=job)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Job updated.")
        return redirect("dashboard")
    return render(request, "jobs/employer_job_form.html", {"form": form, "job": job})


@employer_required
@require_POST
def application_status(request, pk):
    application = get_object_or_404(Application, pk=pk, job__employer=request.user)
    status = request.POST.get("status", "")
    if status in EMPLOYER_STATUSES:
        application.status = status
        application.save(update_fields=["status"])
        messages.success(request, "Status updated.")
    return redirect("dashboard")
