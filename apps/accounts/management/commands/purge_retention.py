import calendar

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.jobs.models import Application
from apps.training.models import Registration


def _months_before(value, months):
    """Calendar-month subtraction, clamping 29 February to the target month."""
    index = value.year * 12 + value.month - 1 - months
    year, month = divmod(index, 12)
    month += 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


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
        months = options["months"]
        if months < 1:
            raise CommandError("--months must be at least 1")
        cutoff = _months_before(timezone.now(), months)
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

        with transaction.atomic():
            application_count = applications.count()
            applications.delete()
            registration_count = uncertified.count()
            uncertified.delete()
            cleared = certified.update(message="")
        self.stdout.write(
            f"Deleted {application_count} applications and {registration_count} "
            f"uncertified registrations; cleared {cleared} messages."
        )
