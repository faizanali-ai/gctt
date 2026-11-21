from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send a test email through the configured transactional backend."

    def add_arguments(self, parser):
        parser.add_argument("recipient", type=str, help="Recipient email address")

    def handle(self, *args, **options):
        recipient = options["recipient"]
        self.stdout.write(self.style.NOTICE("Testing GCTT email configuration..."))
        self.stdout.write(f"  Backend: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"  From: {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"  Recipient: {recipient}")

        try:
            sent = send_mail(
                subject="GCTT Email Setup Verification",
                message=(
                    "This message confirms that the configured transactional "
                    "email backend can send from GCTT.\n\n"
                    "— Global Center for Technology & Training (GCTT)"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
        except Exception as exc:
            raise CommandError(f"Failed to transmit test email: {exc}") from exc

        if not sent:
            raise CommandError("The email backend returned 0 messages sent.")
        self.stdout.write(
            self.style.SUCCESS(f"Test email transmitted to {recipient}.")
        )
