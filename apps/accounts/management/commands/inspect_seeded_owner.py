from django.core.management.base import BaseCommand

from apps.accounts.models import User

SEEDED_EMAILS = (
    "mohdfaizanali30@gmail.com",
    "mohdfaizanali038@gmail.com",
    "ceo@gctekton.com",
)


class Command(BaseCommand):
    help = (
        "Read-only inventory of accounts created by the retired owner-seeding "
        "migrations. Review the output, then decide manually whether to keep, "
        "reset, deactivate or delete each account."
    )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeded-owner inventory"))
        found = 0
        for email in SEEDED_EMAILS:
            users = User.objects.filter(email__iexact=email).order_by("pk")
            if not users.exists():
                self.stdout.write(f"{email}: not present")
                continue
            for user in users:
                found += 1
                self.stdout.write(
                    f"{user.email}: id={user.pk} role={user.role!r} "
                    f"is_staff={user.is_staff} is_superuser={user.is_superuser} "
                    f"is_active={user.is_active} email_verified={user.email_verified}"
                )

        self.stdout.write(f"Found {found} matching account(s). No changes were made.")
        self.stdout.write(
            "Do not delete the current owner. Rotate its password through the "
            "portal or a controlled password-reset flow before removing duplicates."
        )
