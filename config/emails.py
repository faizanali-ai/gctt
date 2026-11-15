from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .constants import COMPANY


def send(to, subject, body):
    # shortcut: synchronous send, move to a task queue when volume justifies it
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to], fail_silently=True)


def verification_url(user, request):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return request.build_absolute_uri(reverse("verify_email", args=[uidb64, token]))


def send_verification(user, request):
    send(
        user.email,
        "Verify your GCTT email address",
        f"Hi {user.display_name},\n\n"
        f"Confirm your email address to finish setting up your GCTT account:\n\n"
        f"{verification_url(user, request)}\n\n"
        f"If you didn't create this account you can ignore this email.",
    )


def notify_enquiry(enquiry):
    send(
        settings.DEFAULT_FROM_EMAIL,
        f"New enquiry: {enquiry.get_category_display()}",
        f"From: {enquiry.name} <{enquiry.email}>\n"
        f"Phone: {enquiry.phone or '—'}\n"
        f"Company: {enquiry.company or '—'}\n"
        f"Category: {enquiry.get_category_display()}\n\n"
        f"{enquiry.message}",
    )


def notify_enquiry_received(enquiry):
    send(
        enquiry.email,
        "We received your enquiry — GCTT",
        f"Hi {enquiry.name},\n\n"
        f"Thanks for contacting GCTT. Your enquiry has been received and our team "
        f"will respond within one business day.\n\n"
        f"For reference, your message was:\n\n{enquiry.message}\n\n"
        f"— GCTT\n{COMPANY['email']}",
    )


def notify_application(application):
    send(
        application.applicant.email,
        f"We received your application: {application.job.title}",
        f"Hi {application.applicant.display_name},\n\n"
        f"Thanks for applying for {application.job.title} ({application.job.location}).\n"
        f"You can track the status of your application on your dashboard.\n\n"
        f"— GCTT",
    )


def notify_staff_new_application(application):
    send(
        COMPANY["jobs_email"],
        f"New application: {application.job.title}",
        f"Candidate: {application.applicant.display_name} <{application.applicant.email}>\n"
        f"Phone: {application.applicant.phone or '—'}\n"
        f"Role: {application.job.title} ({application.job.location})\n\n"
        f"{application.message}\n\n"
        f"Review it in the staff portal: /staff/applications/",
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
        f"Hi {application.applicant.display_name},\n\n"
        f"Your application for {application.job.title} is now "
        f"“{application.get_status_display()}”.\n"
        f"You can see the full history on your dashboard.\n\n"
        f"— GCTT",
    )


def notify_registration(registration):
    send(
        registration.student.email,
        f"Registration received: {registration.programme.title}",
        f"Hi {registration.student.display_name},\n\n"
        f"We received your registration for {registration.programme.title}.\n"
        f"We'll be in touch with the next steps. You can track it on your dashboard.\n\n"
        f"— GCTT",
    )


def notify_registration_status(registration):
    send(
        registration.student.email,
        f"Your training registration is now “{registration.get_status_display()}”",
        f"Hi {registration.student.display_name},\n\n"
        f"Your registration for {registration.programme.title} is now "
        f"“{registration.get_status_display()}”.\n"
        f"You can see the details on your dashboard.\n\n"
        f"— GCTT",
    )


def notify_certificate(registration, request):
    link = request.build_absolute_uri(
        reverse("verify_certificate", args=[registration.certificate_ref])
    )
    send(
        registration.student.email,
        f"Your certificate is ready: {registration.programme.title}",
        f"Hi {registration.student.display_name},\n\n"
        f"Your certificate for {registration.programme.title} has been issued.\n\n"
        f"Certificate ID: {registration.certificate_ref}\n"
        f"Verify it here: {link}\n\n"
        f"— GCTT",
    )
