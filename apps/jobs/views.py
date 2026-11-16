import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from apps.accounts.audit import log_action
from config.emails import (
    notify_application,
    notify_application_status,
    notify_staff_new_application,
)

from .forms import ApplicationForm
from .models import Application, Job

STAFF_STATUSES = {
    Application.Status.UNDER_REVIEW,
    Application.Status.SHORTLISTED,
    Application.Status.REJECTED,
    Application.Status.SELECTED,
}

logger = logging.getLogger(__name__)


def job_list(request):
    jobs = Job.objects.filter(published=True)
    q = request.GET.get("q", "").strip()
    employment_type = request.GET.get("type", "")
    if q:
        jobs = jobs.filter(
            Q(title__icontains=q)
            | Q(location__icontains=q)
            | Q(description__icontains=q)
            | Q(requirements__icontains=q)
        )
    if employment_type:
        jobs = jobs.filter(employment_type=employment_type)
    page_obj = Paginator(jobs, 10).get_page(request.GET.get("page"))
    return render(
        request,
        "jobs/job_list.html",
        {
            "page_obj": page_obj,
            "q": q,
            "type": employment_type,
            "types": Job.EmploymentType.choices,
        },
    )


def job_detail(request, slug):
    job = get_object_or_404(Job, slug=slug)
    if not job.published and not (
        request.user.is_staff and request.user.has_perm("jobs.view_job")
    ):
        raise Http404
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
    form = ApplicationForm(request.POST, request.FILES)
    if form.is_valid():
        application = form.save(commit=False)
        application.job = job
        application.applicant = request.user
        try:
            with transaction.atomic():
                application.save()
            messages.success(request, "Your application has been sent.")
            notify_application(application)
            notify_staff_new_application(application)
        except IntegrityError:
            messages.error(request, "You have already applied to this job.")
        except Exception:
            # Storage or DB failure: never surface a 500 with a lost submission.
            logger.exception("Application submission failed for job %s", job.pk)
            messages.error(
                request,
                "We couldn't store your application just now. Please try again in a "
                "moment, or email jobs@gctekton.com.",
            )
        return redirect("job_detail", slug=job.slug)
    return render(
        request,
        "jobs/job_detail.html",
        {"job": job, "form": form, "applied": False},
    )


@login_required
@require_POST
def withdraw_application(request, pk):
    application = get_object_or_404(Application, pk=pk, applicant=request.user)
    role = application.job.title
    log_action(request, "application.withdraw", f"{application.pk}", role)
    application.delete()
    messages.success(request, f"Your application for {role} was withdrawn.")
    return redirect("dashboard")


@login_required
@permission_required("jobs.view_job", raise_exception=True)
def staff_jobs(request):
    jobs = Job.objects.all()
    q = request.GET.get("q", "").strip()
    published = request.GET.get("published", "")
    if q:
        jobs = jobs.filter(Q(title__icontains=q) | Q(location__icontains=q))
    if published in ("true", "false"):
        jobs = jobs.filter(published=published == "true")
    page_obj = Paginator(jobs, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "staff/jobs.html",
        {"page_obj": page_obj, "q": q, "published": published},
    )


@login_required
@permission_required("jobs.change_job", raise_exception=True)
@require_POST
def staff_job_publish(request, pk):
    job = get_object_or_404(Job, pk=pk)
    job.published = not job.published
    job.save(update_fields=["published"])
    log_action(request, "job.publish", job.title, f"published={job.published}")
    messages.success(request, f"'{job.title}' is now {'published' if job.published else 'a draft'}.")
    return redirect("staff_jobs")


@login_required
@permission_required("jobs.view_application", raise_exception=True)
def staff_applications(request):
    applications = Application.objects.select_related("job", "applicant")
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    job = request.GET.get("job", "")
    if q:
        applications = applications.filter(
            Q(applicant__email__icontains=q)
            | Q(applicant__first_name__icontains=q)
            | Q(applicant__last_name__icontains=q)
            | Q(job__title__icontains=q)
        )
    if status:
        applications = applications.filter(status=status)
    if job:
        applications = applications.filter(job_id=job)
    page_obj = Paginator(applications, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "staff/applications.html",
        {
            "page_obj": page_obj,
            "q": q,
            "status": status,
            "job": job,
            "jobs": Job.objects.all(),
            "statuses": [
                choice for choice in Application.Status.choices if choice[0] in STAFF_STATUSES
            ],
            "all_statuses": Application.Status.choices,
        },
    )


@login_required
@permission_required("jobs.change_application", raise_exception=True)
@require_POST
def staff_application_status(request, pk):
    application = get_object_or_404(Application, pk=pk)
    status = request.POST.get("status", "")
    if status in STAFF_STATUSES:
        previous = application.status
        if previous != status:
            application.status = status
            application.save(update_fields=["status"])
            log_action(request, "application.status", f"{application.pk}", f"{previous} → {status}")
            notify_application_status(application)
            messages.success(request, "Status updated.")
    return redirect("staff_applications")
