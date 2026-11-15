from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = (
        "Dump all application data to a timestamped JSON file. "
        "Use pg_dump against DATABASE_URL for full Postgres backups."
    )

    def add_arguments(self, parser):
        parser.add_argument("--output", type=str, help="Output file path")

    def handle(self, *args, **options):
        target = (
            Path(options["output"])
            if options.get("output")
            else Path("backups") / f"gctt-{timezone.now():%Y%m%d-%H%M%S}.json"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w") as handle:
            call_command(
                "dumpdata",
                exclude=[
                    "contenttypes",
                    "auth.Permission",
                    "sessions.Session",
                    "admin.LogEntry",
                    "otp_totp.TOTPDevice",
                ],
                indent=2,
                stdout=handle,
            )
        self.stdout.write(self.style.SUCCESS(f"Backup written to {target}"))
