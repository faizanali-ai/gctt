from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.jobs.models import Application, PendingApplication
from apps.training.models import PendingRegistration


class Command(BaseCommand):
    help = "Delete expired pending applications/registrations and unreferenced temp resumes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be removed without deleting rows or files.",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        expired_applications = list(
            PendingApplication.objects.filter(expires_at__lt=now)
        )
        expired_registrations = PendingRegistration.objects.filter(
            expires_at__lt=now
        )
        files = [
            pending
            for pending in expired_applications
            if pending.resume
            and not Application.objects.filter(resume=pending.resume.name).exists()
        ]
        if options["dry_run"]:
            self.stdout.write(
                f"Dry run: would purge {len(expired_applications)} pending "
                f"application(s), {expired_registrations.count()} pending "
                f"registration(s), and {len(files)} temp resume(s)."
            )
            return

        applications = 0
        deleted_files = 0
        for pending in expired_applications:
            if pending.resume and not Application.objects.filter(
                resume=pending.resume.name
            ).exists():
                pending.resume.delete(save=False)
                deleted_files += 1
            pending.delete()
            applications += 1

        registrations, _ = expired_registrations.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Purged {applications} pending application(s), "
                f"{registrations} pending registration(s), {deleted_files} temp resume(s)."
            )
        )
