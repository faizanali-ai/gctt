import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.accounts.tokens import email_verification_token_generator

from .constants import COMPANY

logger = logging.getLogger(__name__)

PASSWORD_SETUP_COOLDOWN = 900  # seconds


def _mask_email(email):
    local, _, domain = (email or "").partition("@")
    return f"{local[:2]}***@{domain}" if domain else "***"


def send(to, subject, body):
    recipients = [to] if isinstance(to, str) else list(to)
    sent = 0
    for recipient in recipients:
        try:
            send_mail(
                subject, body, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=False
            )
            sent += 1
        except Exception:
            logger.exception(
                "Failed to send email to %s (subject: %s)",
                _mask_email(recipient),
                subject,
            )
    return sent


def staff_recipients(subgroup):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    recipients = list(
        User.objects.filter(is_active=True, is_staff=True, groups__name=subgroup)
        .values_list("email", flat=True)
        .distinct()
    )
    if not recipients:
        # Never let a queue alert vanish because a subgroup is empty.
        recipients = list(
            User.objects.filter(is_active=True, role=User.Role.ADMIN)
            .values_list("email", flat=True)
            .distinct()
        )
        if recipients:
            logger.warning(
                "No active %s staff; falling back to active admins", subgroup
            )
    return recipients


def notify_subgroup(subgroup, subject, body):
    recipients = staff_recipients(subgroup)
    if recipients:
        send(recipients, subject, body)
    else:
        logger.warning("No active %s staff recipient for: %s", subgroup, subject)


def send_password_setup(user):
    key = f"password-setup:{user.email.lower()}"
    if not cache.add(key, True, PASSWORD_SETUP_COOLDOWN):
        logger.info(
            "Password setup email throttled for %s", _mask_email(user.email)
        )
        return False

    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    base = getattr(settings, "SITE_URL", "https://gctekton.com").rstrip("/")
    link = f"{base}{reverse('password_reset_confirm', args=[uidb64, token])}"
    sent = send(
        user.email,
        "Set your GCTT account password",
        f"Dear {user.display_name},\n\n"
        "Use the secure link below to set or reset the password for your GCTT account:\n\n"
        f"{link}\n\n"
        "If you did not request this, no action is required.\n\n"
        "Global Center for Technology & Training (GCTT)",
    )
    if not sent:
        cache.delete(key)
    return bool(sent)


def verification_url(user, request=None):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token_generator.make_token(user)
    base = getattr(settings, "SITE_URL", "https://gctekton.com").rstrip("/")
    path = reverse("verify_email", args=[uidb64, token])
    return f"{base}{path}"


def send_verification(user, request):
    send(
        user.email,
        "Verify your GCTT email address",
        f"Dear {user.display_name},\n\n"
        f"Thank you for registering with the Global Center for Technology & Training (GCTT).\n\n"
        f"To complete your account activation and access your authenticated candidate or learner portal, please confirm your email address by following this secure link:\n\n"
        f"{verification_url(user, request)}\n\n"
        f"If you did not initiate this registration, no further action is required.\n\n"
        f"Warm regards,\n\n"
        f"Executive Admissions & Talent Governance\n"
        f"Global Center for Technology & Training (GCTT)\n"
        f"{COMPANY['address']}\n"
        f"{COMPANY['email']}",
    )


def notify_enquiry(enquiry):
    notify_subgroup(
        "Enquiry Manager",
        f"New enterprise enquiry: {enquiry.get_category_display()}",
        f"From: {enquiry.name} <{enquiry.email}>\n"
        f"Phone: {enquiry.phone or '—'}\n"
        f"Company: {enquiry.company or '—'}\n"
        f"Category: {enquiry.get_category_display()}\n"
        f"Area: {enquiry.area or '—'}\n"
        f"How heard: {enquiry.how_heard or '—'}\n\n"
        f"Executive Message:\n"
        f"{enquiry.message}",
    )


def notify_enquiry_received(enquiry):
    send(
        enquiry.email,
        "We received your enquiry — GCTT",
        f"Dear {enquiry.name},\n\n"
        f"Thank you for contacting the Global Center for Technology & Training (GCTT).\n\n"
        f"We have received your enquiry regarding “{enquiry.get_category_display()}”. A dedicated practice director from our Irving, Texas headquarters will review your specifications and follow up within 24 business hours.\n\n"
        f"Warm regards,\n\n"
        f"Corporate Advisory Practice\n"
        f"Global Center for Technology & Training (GCTT)\n"
        f"{COMPANY['address']}\n"
        f"{COMPANY['email']}",
    )


def notify_application(application):
    send(
        application.applicant.email,
        f"We received your application: {application.job.title}",
        f"Dear {application.applicant.display_name},\n\n"
        f"Thank you for applying for the {application.job.title} engagement ({application.job.location}) with GCTT.\n\n"
        f"Your resume and candidate dossier have been submitted directly to our practice recruiting team. We evaluate candidates on hands-on architectural capability, project track record, and delivery velocity.\n\n"
        f"You may monitor the real-time review status of your submission directly via your authenticated candidate dashboard.\n\n"
        f"Warm regards,\n\n"
        f"Technical Search & Talent Acquisition Practice\n"
        f"Global Center for Technology & Training (GCTT)\n"
        f"{COMPANY['jobs_email']}",
    )


def notify_staff_new_application(application):
    notify_subgroup(
        "Recruiter",
        f"New application: {application.job.title}",
        f"Candidate: {application.applicant.display_name} <{application.applicant.email}>\n"
        f"Phone: {application.applicant.phone or '—'}\n"
        f"Mandate: {application.job.title} ({application.job.location})\n\n"
        f"Candidate Note:\n{application.message}\n\n"
        f"Review candidate dossier in the staff portal: /staff/applications/",
    )


def notify_application_status(application):
    subject = {
        "shortlisted": f"You've been shortlisted for {application.job.title}",
        "selected": f"Good news about your application: {application.job.title}",
        "rejected": f"Update on your application: {application.job.title}",
    }.get(application.status, f"Your application status changed: {application.job.title}")
    send(
        application.applicant.email,
        subject,
        f"Dear {application.applicant.display_name},\n\n"
        f"We are providing an update on your candidacy for the {application.job.title} engagement.\n\n"
        f"Your application status has advanced to: “{application.get_status_display()}”.\n\n"
        f"Please log in to your candidate dashboard to review upcoming interview milestones and direct recruiter notes.\n\n"
        f"Warm regards,\n\n"
        f"Executive Talent Acquisition Team\n"
        f"Global Center for Technology & Training (GCTT)\n"
        f"{COMPANY['jobs_email']}",
    )


def notify_registration(registration):
    send(
        registration.student.email,
        f"Registration received: {registration.programme.title}",
        f"Dear {registration.student.display_name},\n\n"
        f"We have received your cohort enrolment registration for “{registration.programme.title}”.\n\n"
        f"Our education practice coordinators will verify prerequisites, calendar schedules, and enterprise sandbox access, and will contact you with onboarding instructions.\n\n"
        f"You can monitor cohort announcements and credential milestones from your authenticated dashboard.\n\n"
        f"Warm regards,\n\n"
        f"Workforce Development & Academy\n"
        f"Global Center for Technology & Training (GCTT)\n"
        f"{COMPANY['email']}",
    )


def notify_staff_new_registration(registration):
    notify_subgroup(
        "Trainer",
        f"New training registration: {registration.programme.title}",
        f"Student: {registration.student.display_name} <{registration.student.email}>\n"
        f"Phone: {registration.student.phone or '—'}\n"
        f"Programme: {registration.programme.title}\n\n"
        f"Registration Note:\n{registration.message or 'No message provided.'}\n\n"
        f"Review in the staff portal: /staff/registrations/",
    )


def notify_registration_status(registration):
    send(
        registration.student.email,
        f"Your training registration is now “{registration.get_status_display()}”",
        f"Dear {registration.student.display_name},\n\n"
        f"Your registration status for “{registration.programme.title}” has been updated to: “{registration.get_status_display()}”.\n\n"
        f"Please check your student dashboard for syllabus updates and scheduled sessions.\n\n"
        f"Warm regards,\n\n"
        f"Workforce Development & Academy\n"
        f"Global Center for Technology & Training (GCTT)\n"
        f"{COMPANY['email']}",
    )


def notify_certificate(registration, request):
    link = request.build_absolute_uri(
        reverse("verify_certificate", args=[registration.certificate_ref])
    )
    send(
        registration.student.email,
        f"Your certificate is ready: {registration.programme.title}",
        f"Dear {registration.student.display_name},\n\n"
        f"Congratulations on successfully fulfilling all academic and project requirements for “{registration.programme.title}”.\n\n"
        f"Your official digital credential has been minted and permanently recorded:\n\n"
        f"Unique Certificate Reference: {registration.certificate_ref}\n"
        f"Public Verification Plaque: {link}\n\n"
        f"You can share this authenticated credential with enterprise employers and add it directly to your LinkedIn profile from your dashboard.\n\n"
        f"Warm regards,\n\n"
        f"Academic Board & Certification Registry\n"
        f"Global Center for Technology & Training (GCTT)\n"
        f"{COMPANY['email']}",
    )
