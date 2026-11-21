from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.jobs.models import Application
from apps.training.models import Registration


class Command(BaseCommand):
    help = "Delete records past the retention window (dry-run unless --apply)."

    def add_arguments(self, parser):
        parser.add_argument("--months", type=int, default=24)
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Delete and update records instead of previewing counts.",
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options["months"] * 30)
        applications = Application.objects.filter(created_at__lt=cutoff)
        uncertified = Registration.objects.filter(
            created_at__lt=cutoff, certificate_issued=False
        )
        certified = Registration.objects.filter(
            created_at__lt=cutoff, certificate_issued=True
        ).exclude(message="")

        self.stdout.write(f"Retention cutoff: {cutoff.date().isoformat()}")
        self.stdout.write(f"Applications to delete: {applications.count()}")
        self.stdout.write(f"Uncertified registrations to delete: {uncertified.count()}")
        self.stdout.write(f"Certified messages to clear: {certified.count()}")
        self.stdout.write("Pending submissions and audit logs are left untouched.")

        if not options["apply"]:
            self.stdout.write("Dry run; pass --apply to delete.")
            return

        application_count = applications.count()
        applications.delete()
        registration_count = uncertified.count()
        uncertified.delete()
        cleared = certified.update(message="")
        self.stdout.write(
            f"Deleted {application_count} applications and {registration_count} "
            f"uncertified registrations; cleared {cleared} messages."
        )
