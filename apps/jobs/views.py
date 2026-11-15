from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from .forms import ApplicationForm
from .models import Job


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
