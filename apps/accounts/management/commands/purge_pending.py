from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.jobs.models import Application, PendingApplication
from apps.training.models import PendingRegistration


class Command(BaseCommand):
    help = "Delete expired pending applications/registrations and unreferenced temp resumes."

    def handle(self, *args, **options):
        now = timezone.now()
        applications = 0
        files = 0
        for pending in PendingApplication.objects.filter(expires_at__lt=now):
            if pending.resume and not Application.objects.filter(
                resume=pending.resume.name
            ).exists():
                pending.resume.delete(save=False)
                files += 1
            pending.delete()
            applications += 1

        registrations, _ = PendingRegistration.objects.filter(
            expires_at__lt=now
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Purged {applications} pending application(s), "
                f"{registrations} pending registration(s), {files} temp resume(s)."
            )
        )
