from django.core.management.base import BaseCommand

from apps.accounts.email_otp import purge_expired


class Command(BaseCommand):
    help = "Delete expired or consumed email OTP rows."

    def handle(self, *args, **options):
        deleted = purge_expired()
        self.stdout.write(
            self.style.SUCCESS(f"Purged {deleted} email OTP row(s).")
        )
