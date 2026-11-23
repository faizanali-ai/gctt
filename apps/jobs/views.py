import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, permission_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from apps.accounts.audit import log_action
from apps.accounts.decorators import staff_required
from apps.accounts.models import SiteSettings, User
from apps.accounts.pending import expiry, hash_token, make_token
from config.emails import (
    notify_application,
    notify_application_status,
    notify_staff_new_application,
    send_password_setup,
    send_pending_application,
    send_welcome_if_first_login,
)

from .forms import ApplicationForm, ApplicationManageForm, JobForm
from .models import Application, Job, PendingApplication

STAFF_STATUSES = {
    Application.Status.UNDER_REVIEW,
    Application.Status.SHORTLISTED,
    Application.Status.REJECTED,
    Application.Status.SELECTED,
}

logger = logging.getLogger(__name__)


def _notify_safely(label, callback):
    try:
        callback()
    except Exception:
        logger.exception("Notification failed: %s", label)


def _message_with_work_auth(form):
    message = form.cleaned_data["message"]
    work_auth = form.cleaned_data.get("work_authorization")
    if work_auth:
        label = dict(form.fields["work_authorization"].choices).get(work_auth, work_auth)
        message = f"[Work Auth: {label}]\n{message}"
    return message


def _create_pending_application(job, email, resume, message):
    cooldown_key = f"pending-application:{job.pk}:{email.lower()}"
    if not cache.add(cooldown_key, True, 300):
        return None
    token, token_hash = make_token()
    pending = PendingApplication.objects.create(
        job=job,
        email=email,
        resume=resume,
        message=message,
        token_hash=token_hash,
        expires_at=expiry(),
    )
    send_pending_application(pending, token)
    return pending


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
    initial = {}
    if request.user.is_authenticated:
        initial = {
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "email": request.user.email,
            "phone": getattr(request.user, "phone", ""),
        }
    form = ApplicationForm(is_authenticated=request.user.is_authenticated, initial=initial)
    return render(
        request,
        "jobs/job_detail.html",
        {"job": job, "form": form, "applied": applied},
    )


@require_POST
@ratelimit(key="ip", rate="30/h", method="POST", block=True)
def job_apply(request, slug):
    job = get_object_or_404(Job, slug=slug, published=True)
    try:
        allow_applications = SiteSettings.load().allow_candidate_applications
    except DatabaseError:
        allow_applications = False
    if not allow_applications:
        messages.error(request, "Candidate applications are currently paused by the administrator.")
        return redirect("job_detail", slug=job.slug)
    is_auth = request.user.is_authenticated
    form = ApplicationForm(request.POST, request.FILES, is_authenticated=is_auth)
    if form.is_valid():
        generic_message = "If this email can be used, check your inbox to continue."
        message = _message_with_work_auth(form)
        resume = form.cleaned_data["resume"]
        if is_auth:
            user = request.user
            if not user.is_candidate:
                messages.error(request, "Use a candidate account to apply for roles.")
                return redirect("job_detail", slug=job.slug)
            if settings.REQUIRE_VERIFIED_EMAIL_ACTIONS and not user.email_verified:
                messages.error(
                    request,
                    "Verify your email address before applying for roles.",
                )
                return redirect("dashboard")
        else:
            email = form.cleaned_data["email"].strip().lower()
            first_name = form.cleaned_data.get("first_name", "").strip()
            last_name = form.cleaned_data.get("last_name", "").strip()
            phone = form.cleaned_data.get("phone", "").strip()

            existing_user = User.objects.filter(email__iexact=email).first()
            if existing_user:
                if existing_user.is_candidate:
                    _create_pending_application(
                        job, existing_user.email, resume, message
                    )
                messages.info(request, generic_message)
                return redirect("job_detail", slug=job.slug)

            try:
                user = User.objects.create_user(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    account_type=User.AccountType.CANDIDATE,
                )
                user.set_unusable_password()
                user.save()
            except IntegrityError:
                existing_user = User.objects.filter(email__iexact=email).first()
                if existing_user:
                    _create_pending_application(
                        job, existing_user.email, resume, message
                    )
                messages.info(request, generic_message)
                return redirect("job_detail", slug=job.slug)

        application = Application(
            job=job,
            applicant=user,
            resume=resume,
            message=message,
        )
        try:
            with transaction.atomic():
                application.save()
        except IntegrityError:
            messages.error(request, "You have already applied to this job.")
            return redirect("job_detail", slug=job.slug)
        except Exception:
            # Storage or DB failure: never surface a 500 with a lost submission.
            logger.exception("Application submission failed for job %s", job.pk)
            messages.error(
                request,
                "We couldn't store your application just now. Please try again in a "
                "moment, or email jobs@gctekton.com.",
            )
            return redirect("job_detail", slug=job.slug)

        _notify_safely("application", lambda: notify_application(application))
        _notify_safely(
            "staff application", lambda: notify_staff_new_application(application)
        )
        if is_auth:
            messages.success(request, "Your application has been received by GCTT technical recruitment directors.")
            return redirect("dashboard")
        _notify_safely("password setup", lambda: send_password_setup(user))
        messages.info(request, generic_message)
        return redirect("job_detail", slug=job.slug)
    return render(
        request,
        "jobs/job_detail.html",
        {"job": job, "form": form, "applied": False},
    )


@ratelimit(key="ip", rate="30/m", block=True)
def pending_application(request, token):
    pending = get_object_or_404(
        PendingApplication,
        token_hash=hash_token(token),
        consumed_at__isnull=True,
        expires_at__gt=timezone.now(),
    )
    user = User.objects.filter(email__iexact=pending.email, is_active=True).first()
    if not user:
        raise Http404
    if request.user.is_authenticated and request.user.pk != user.pk:
        raise Http404
    if not user.is_candidate:
        messages.error(request, "Use a candidate account to apply for roles.")
        return redirect("login")
    site_settings = SiteSettings.load()
    if not site_settings.allow_candidate_applications:
        messages.error(request, "Candidate applications are currently paused.")
        return redirect("dashboard")
    if not request.user.is_authenticated:
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        send_welcome_if_first_login(user)

    if request.method == "POST":
        if Application.objects.filter(job=pending.job, applicant=user).exists():
            pending.consumed_at = timezone.now()
            pending.save(update_fields=["consumed_at"])
            messages.info(request, "You have already applied to this job.")
            return redirect("dashboard")
        application = Application(
            job=pending.job,
            applicant=user,
            resume=pending.resume.name,
            message=request.POST.get("message", pending.message)[:4000],
        )
        try:
            with transaction.atomic():
                application.save()
                pending.consumed_at = timezone.now()
                pending.save(update_fields=["consumed_at"])
        except IntegrityError:
            messages.info(request, "You have already applied to this job.")
            return redirect("dashboard")
        _notify_safely("application", lambda: notify_application(application))
        _notify_safely(
            "staff application", lambda: notify_staff_new_application(application)
        )
        messages.success(
            request,
            "Your application has been received by GCTT technical recruitment directors.",
        )
        return redirect("dashboard")

    return render(
        request,
        "jobs/pending_application.html",
        {"pending": pending},
    )


@login_required
@require_POST
def withdraw_application(request, uuid=None, pk=None):
    applications = Application.objects.filter(applicant=request.user)
    application = get_object_or_404(
        applications,
        **({"uuid": uuid} if uuid else {"pk": pk}),
    )
    role = application.job.title
    log_action(request, "application.withdraw", f"{application.pk}", role)
    application.delete()
    messages.success(request, f"Your application for {role} was withdrawn.")
    return redirect("dashboard")


@login_required
@staff_required
@permission_required("jobs.view_job", raise_exception=True)
def staff_jobs(request):
    jobs = Job.objects.annotate(application_count=Count("applications"))
    q = request.GET.get("q", "").strip()
    published = request.GET.get("published", "")
    if q:
        jobs = jobs.filter(Q(title__icontains=q) | Q(location__icontains=q))
    if published in ("true", "false"):
        jobs = jobs.filter(published=published == "true")
    page_obj = Paginator(jobs, 25).get_page(request.GET.get("page"))
    from .linkedin import generate_linkedin_post_text

    for job in page_obj:
        job.linkedin_post_text = generate_linkedin_post_text(job, request)
    return render(
        request,
        "staff/jobs.html",
        {"page_obj": page_obj, "q": q, "published": published},
    )


@login_required
@staff_required
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
@staff_required
@permission_required("jobs.view_application", raise_exception=True)
def staff_applications(request):
    applications = Application.objects.select_related("job", "applicant").filter(
        applicant__is_staff=False
    )
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
        applications = (
            applications.filter(job_id=job)
            if job.isdigit()
            else applications.none()
        )
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
@staff_required
@permission_required("jobs.change_application", raise_exception=True)
@require_POST
def staff_application_status(request, uuid=None, pk=None):
    application = get_object_or_404(
        Application.objects.filter(applicant__is_staff=False),
        **({"uuid": uuid} if uuid else {"pk": pk}),
    )
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


@login_required
@staff_required
@permission_required("jobs.add_job", raise_exception=True)
def staff_job_create(request):
    form = JobForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        job = form.save()
        log_action(request, "job.create", job.title, f"published={job.published}")
        messages.success(request, f"'{job.title}' created.")
        return redirect("staff_jobs")
    return render(request, "staff/job_form.html", {"form": form, "mode": "create"})


@login_required
@staff_required
@permission_required("jobs.change_job", raise_exception=True)
def staff_job_edit(request, pk):
    job = get_object_or_404(Job, pk=pk)
    form = JobForm(request.POST or None, instance=job)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(request, "job.edit", job.title, f"published={job.published}")
        messages.success(request, "Mandate updated.")
        return redirect("staff_jobs")
    return render(
        request,
        "staff/job_form.html",
        {"form": form, "mode": "edit", "job": job},
    )


@login_required
@staff_required
@permission_required("jobs.delete_job", raise_exception=True)
@require_POST
def staff_job_delete(request, pk):
    job = get_object_or_404(Job, pk=pk)
    title = job.title
    job.delete()
    log_action(request, "job.delete", title)
    messages.success(request, f"'{title}' deleted.")
    return redirect("staff_jobs")


@login_required
@staff_required
@permission_required("jobs.change_application", raise_exception=True)
def staff_application_edit(request, uuid):
    application = get_object_or_404(
        Application.objects.select_related("job", "applicant").filter(
            applicant__is_staff=False
        ),
        uuid=uuid,
    )
    form = ApplicationManageForm(request.POST or None, instance=application)
    if request.method == "POST" and form.is_valid():
        previous = application.status
        form.save()
        log_action(
            request,
            "application.edit",
            f"{application.pk}",
            f"{previous} → {application.status}",
        )
        if previous != application.status:
            notify_application_status(application)
        messages.success(request, "Application updated.")
        return redirect("staff_applications")
    return render(
        request,
        "staff/application_detail.html",
        {"form": form, "application": application},
    )


@login_required
@staff_required
@permission_required("jobs.delete_application", raise_exception=True)
@require_POST
def staff_application_delete(request, uuid):
    application = get_object_or_404(
        Application.objects.filter(applicant__is_staff=False), uuid=uuid
    )
    label = f"{application.applicant.email} → {application.job.title}"
    application.delete()
    log_action(request, "application.delete", label)
    messages.success(request, "Application deleted.")
    return redirect("staff_applications")


@login_required
@staff_required
@permission_required("jobs.change_application", raise_exception=True)
@require_POST
def staff_applications_bulk(request):
    status = request.POST.get("bulk_status", "")
    selected = request.POST.getlist("selected")
    if status not in STAFF_STATUSES or not selected:
        messages.error(request, "Select applications and a valid status.")
        return redirect("staff_applications")
    try:
        ids = {int(value) for value in selected}
    except (TypeError, ValueError):
        messages.error(request, "Select applications and a valid status.")
        return redirect("staff_applications")

    applications = list(
        Application.objects.filter(
            pk__in=ids, applicant__is_staff=False
        ).select_related("applicant", "job")
    )
    changed = [application for application in applications if application.status != status]
    with transaction.atomic():
        for application in changed:
            application.status = status
            application.save(update_fields=["status"])
        log_action(
            request,
            "application.bulk_status",
            f"{len(changed)} application(s)",
            f"ids={sorted(ids)} status={status}",
        )
    for application in changed:
        _notify_safely(
            "application status",
            lambda application=application: notify_application_status(application),
        )
    messages.success(request, f"{len(changed)} application(s) updated.")
    return redirect("staff_applications")


@login_required
@staff_required
@permission_required("jobs.change_job", raise_exception=True)
@require_POST
def staff_job_linkedin_post(request, pk):
    from .linkedin import generate_linkedin_share_url, post_job_to_linkedin

    job = get_object_or_404(Job, pk=pk)
    if not job.published:
        messages.error(request, "Please publish the job mandate before sharing to LinkedIn.")
        return redirect("staff_jobs")

    res = post_job_to_linkedin(job, request)
    if res.get("success"):
        messages.success(request, f"Successfully published '{job.title}' to GCTT's LinkedIn Organization Page!")
    else:
        share_url = res.get("share_url") or generate_linkedin_share_url(job, request)
        reason = res.get("message") or "LinkedIn publishing failed."
        messages.info(
            request,
            f"{reason} You can share manually using: {share_url}"
        )
    return redirect("staff_jobs")
