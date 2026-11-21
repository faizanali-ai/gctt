import logging
import time

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.accounts.tokens import email_verification_token_generator

from .site import company

logger = logging.getLogger(__name__)

PASSWORD_SETUP_COOLDOWN = 900  # seconds
PROMOTIONAL_OPT_IN_MAX_AGE = 7 * 24 * 60 * 60
PROMOTIONAL_OPT_IN_COOLDOWN = 60


def _company():
    return company()


def _brand():
    return _company()["name"]


def _legal():
    return f"{_company()['legal_name']} ({_company()['name']})"


def _mask_email(email):
    local, _, domain = (email or "").partition("@")
    return f"{local[:2]}***@{domain}" if domain else "***"


def send(to, subject, body, html_body=None, headers=None):
    recipients = [to] if isinstance(to, str) else list(to)
    sent = 0
    retries = max(0, int(getattr(settings, "EMAIL_SEND_RETRIES", 1)))
    delay = max(0.0, float(getattr(settings, "EMAIL_RETRY_DELAY_SECONDS", 0.5)))

    for recipient in recipients:
        for attempt in range(retries + 1):
            try:
                message = EmailMultiAlternatives(
                    subject,
                    body,
                    settings.DEFAULT_FROM_EMAIL,
                    [recipient],
                    headers=headers or None,
                )
                if html_body:
                    message.attach_alternative(html_body, "text/html")
                if message.send(fail_silently=False):
                    sent += 1
                break
            except Exception:
                if attempt < retries:
                    logger.warning(
                        "Transient email failure for %s (subject: %s); retrying",
                        _mask_email(recipient),
                        subject,
                    )
                    if delay:
                        time.sleep(delay)
                    continue
                logger.exception(
                    "Failed to send email to %s (subject: %s)",
                    _mask_email(recipient),
                    subject,
                )
    return sent


def _site_url():
    return getattr(settings, "SITE_URL", "https://gctekton.com").rstrip("/")


def promotional_unsubscribe_url(user):
    token = signing.dumps({"uid": user.pk}, salt="gctt-promotional-unsubscribe")
    return f"{_site_url()}{reverse('promotional_unsubscribe', args=[token])}"


def _render_email(text_template, html_template, context):
    context = {
        **context,
        "company": _company(),
        "site_url": _site_url(),
    }
    return (
        render_to_string(text_template, context),
        render_to_string(html_template, context),
    )


def send_welcome(user):
    text, html = _render_email(
        "emails/welcome.txt", "emails/welcome.html", {"user": user}
    )
    return bool(
        send(user.email, f"Welcome to {_brand()}", text, html_body=html)
    )


def send_welcome_if_first_login(user):
    """Send exactly one welcome email, after the first successful login."""
    if user.welcome_email_sent_at:
        return False
    try:
        if not send_welcome(user):
            return False
    except Exception:
        logger.exception("Failed to prepare welcome email for %s", _mask_email(user.email))
        return False
    sent_at = timezone.now()
    try:
        type(user).objects.filter(
            pk=user.pk, welcome_email_sent_at__isnull=True
        ).update(welcome_email_sent_at=sent_at)
    except Exception:
        logger.exception(
            "Welcome email sent but timestamp update failed for %s",
            _mask_email(user.email),
        )
        return False
    user.welcome_email_sent_at = sent_at
    return True


def promotional_opt_in_url(user):
    token = signing.TimestampSigner(salt="gctt-promotional-opt-in").sign(
        str(user.pk)
    )
    return f"{_site_url()}{reverse('promotional_opt_in_confirm', args=[token])}"


def send_promotional_opt_in(user):
    key = f"promotional-opt-in:{user.pk}"
    if not cache.add(key, True, PROMOTIONAL_OPT_IN_COOLDOWN):
        return False
    try:
        text, html = _render_email(
            "emails/promotional_opt_in.txt",
            "emails/promotional_opt_in.html",
            {"user": user, "confirm_url": promotional_opt_in_url(user)},
        )
        sent = send(
            user.email,
            f"Confirm your {_brand()} email preferences",
            text,
            html_body=html,
        )
    except Exception:
        logger.exception(
            "Failed to prepare promotional opt-in email for %s",
            _mask_email(user.email),
        )
        cache.delete(key)
        return False
    if not sent:
        cache.delete(key)
    return bool(sent)


def send_promotional(user, subject, content):
    try:
        unsubscribe_url = promotional_unsubscribe_url(user)
        text, html = _render_email(
            "emails/promotional.txt",
            "emails/promotional.html",
            {"user": user, "content": content, "unsubscribe_url": unsubscribe_url},
        )
    except Exception:
        logger.exception(
            "Failed to prepare promotional email for %s", _mask_email(user.email)
        )
        return False
    return bool(
        send(
            user.email,
            subject,
            text,
            html_body=html,
            headers={"List-Unsubscribe": f"<{unsubscribe_url}>"},
        )
    )


def staff_recipients(subgroup):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return list(
        User.objects.filter(is_active=True, is_staff=True, groups__name=subgroup)
        .values_list("email", flat=True)
        .distinct()
    )


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
        f"Set your {_brand()} account password",
        f"Dear {user.display_name},\n\n"
        f"Use the secure link below to set or reset the password for your {_brand()} account:\n\n"
        f"{link}\n\n"
        "If you did not request this, no action is required.\n\n"
        f"{_legal()}",
    )
    if not sent:
        cache.delete(key)
    return bool(sent)


def send_login_otp(email, code):
    minutes = max(1, int(getattr(settings, "EMAIL_OTP_TTL_SECONDS", 600)) // 60)
    return bool(
        send(
            email,
            f"Your {_brand()} sign-in code",
            f"Your one-time {_brand()} sign-in code is:\n\n"
            f"{code}\n\n"
            f"It expires in {minutes} minutes. If you did not request it, ignore this email.\n\n"
            f"{_legal()}",
        )
    )


def verification_url(user, request=None):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token_generator.make_token(user)
    base = getattr(settings, "SITE_URL", "https://gctekton.com").rstrip("/")
    path = reverse("verify_email", args=[uidb64, token])
    return f"{base}{path}"


def send_verification(user, request):
    send(
        user.email,
        f"Verify your {_brand()} email address",
        f"Dear {user.display_name},\n\n"
        f"Thank you for registering with the {_legal()}.\n\n"
        f"To complete your account activation and access your authenticated candidate or learner portal, please confirm your email address by following this secure link:\n\n"
        f"{verification_url(user, request)}\n\n"
        f"If you did not initiate this registration, no further action is required.\n\n"
        f"Warm regards,\n\n"
        f"Executive Admissions & Talent Governance\n"
        f"{_legal()}\n"
        f"{_company()['address']}\n"
        f"{_company()['email']}",
    )


def send_pending_application(pending, token):
    link = (
        f"{getattr(settings, 'SITE_URL', 'https://gctekton.com').rstrip('/')}"
        f"{reverse('pending_application', args=[token])}"
    )
    send(
        pending.email,
        f"Continue your application: {pending.job.title}",
        "Use the single-use link below to sign in and confirm your application. "
        "It expires in 24 hours.\n\n"
        f"{link}\n\n"
        f"{_legal()}",
    )


def send_pending_registration(pending, token):
    link = (
        f"{getattr(settings, 'SITE_URL', 'https://gctekton.com').rstrip('/')}"
        f"{reverse('pending_registration', args=[token])}"
    )
    send(
        pending.email,
        f"Continue your registration: {pending.programme.title}",
        "Use the single-use link below to sign in and confirm your registration. "
        "It expires in 24 hours.\n\n"
        f"{link}\n\n"
        f"{_legal()}",
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
        f"We received your enquiry — {_brand()}",
        f"Dear {enquiry.name},\n\n"
        f"Thank you for contacting the {_legal()}.\n\n"
        f"We have received your enquiry regarding “{enquiry.get_category_display()}”. A dedicated practice director from our Irving, Texas headquarters will review your specifications and follow up within 24 business hours.\n\n"
        f"Warm regards,\n\n"
        f"Corporate Advisory Practice\n"
        f"{_legal()}\n"
        f"{_company()['address']}\n"
        f"{_company()['email']}",
    )


def notify_application(application):
    send(
        application.applicant.email,
        f"We received your application: {application.job.title}",
        f"Dear {application.applicant.display_name},\n\n"
        f"Thank you for applying for the {application.job.title} engagement ({application.job.location}) with {_brand()}.\n\n"
        f"Your resume and candidate dossier have been submitted directly to our practice recruiting team. We evaluate candidates on hands-on architectural capability, project track record, and delivery velocity.\n\n"
        f"You may monitor the real-time review status of your submission directly via your authenticated candidate dashboard.\n\n"
        f"Warm regards,\n\n"
        f"Technical Search & Talent Acquisition Practice\n"
        f"{_legal()}\n"
        f"{_company()['jobs_email']}",
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
        f"{_legal()}\n"
        f"{_company()['jobs_email']}",
    )


def notify_registration(registration):
    text, html = _render_email(
        "emails/enrollment.txt",
        "emails/enrollment.html",
        {"registration": registration, "student": registration.student},
    )
    send(
        registration.student.email,
        f"Registration received: {registration.programme.title}",
        text,
        html_body=html,
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
        f"{_legal()}\n"
        f"{_company()['email']}",
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
        f"{_legal()}\n"
        f"{_company()['email']}",
    )
