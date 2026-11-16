from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Send a test email to verify SMTP configuration and connectivity."

    def add_arguments(self, parser):
        parser.add_argument("recipient", type=str, help="Recipient email address")

    def handle(self, *args, **options):
        recipient = options["recipient"]
        self.stdout.write(self.style.NOTICE("Testing GCTT Email Configuration..."))
        self.stdout.write(f"  Backend: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"  Host: {settings.EMAIL_HOST or '(not set)'}")
        self.stdout.write(f"  Port: {settings.EMAIL_PORT}")
        self.stdout.write(f"  User: {settings.EMAIL_HOST_USER or '(not set)'}")
        self.stdout.write(f"  Password configured: {'Yes' if settings.EMAIL_HOST_PASSWORD else 'No'}")
        self.stdout.write(f"  Use TLS: {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"  Use SSL: {settings.EMAIL_USE_SSL}")
        self.stdout.write(f"  Default From: {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"  Sending test email to: {recipient}...")

        try:
            sent = send_mail(
                subject="GCTT Email Setup Verification",
                message=(
                    "Congratulations!\n\n"
                    "Your GCTT email integration is functioning correctly.\n"
                    "This test confirms that your SMTP credentials, TLS handshake, "
                    "and sender addresses are properly calibrated.\n\n"
                    "— Global Center for Technology & Training (GCTT)"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            if sent:
                self.stdout.write(self.style.SUCCESS(f"✓ Test email successfully transmitted to {recipient}!"))
            else:
                self.stdout.write(self.style.WARNING("! send_mail returned 0 messages sent."))
        except Exception as exc:  # noqa: BLE001
            self.stdout.write(self.style.ERROR(f"✗ Failed to transmit test email: {exc}"))
