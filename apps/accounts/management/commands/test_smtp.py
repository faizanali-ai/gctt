import sys

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Test SMTP configuration by sending a verification test email."

    def add_arguments(self, parser):
        parser.add_argument(
            "recipient",
            nargs="?",
            default=settings.DEFAULT_FROM_EMAIL,
            help="Recipient email address (defaults to DEFAULT_FROM_EMAIL)",
        )

    def handle(self, *args, **options):
        recipient = options["recipient"]
        self.stdout.write(self.style.NOTICE(f"Testing email sending via {settings.EMAIL_BACKEND}..."))
        self.stdout.write(f"EMAIL_HOST: {settings.EMAIL_HOST or '(none - console)'}")
        self.stdout.write(f"EMAIL_PORT: {settings.EMAIL_PORT}")
        self.stdout.write(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"Recipient: {recipient}")

        try:
            sent = send_mail(
                subject="[GCTT] SMTP Connectivity Test",
                message="This is a test email sent from GCTekton to verify SMTP delivery.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            if sent:
                self.stdout.write(self.style.SUCCESS(f"Successfully sent test email to {recipient}."))
            else:
                self.stdout.write(self.style.WARNING("send_mail returned 0 messages sent."))
        except Exception as exc:  # noqa: BLE001
            self.stderr.write(self.style.ERROR(f"Failed to send email: {exc}"))
            sys.exit(1)
