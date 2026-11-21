from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from config import legacy


class Command(BaseCommand):
    help = "Report legacy numeric URLs and fail once the sunset date has passed."

    def add_arguments(self, parser):
        parser.add_argument("--date", help="Override today's date (YYYY-MM-DD).")

    def handle(self, *args, **options):
        today = (
            date.fromisoformat(options["date"])
            if options["date"]
            else timezone.localdate()
        )
        live = []
        for name in sorted(legacy.LEGACY_URL_NAMES):
            try:
                reverse(name, args=[1])
            except NoReverseMatch:
                continue
            live.append(name)

        for name in live:
            self.stdout.write(f"legacy: {name}")
        if not live:
            self.stdout.write("No legacy numeric URLs are registered.")
        elif today >= legacy.SUNSET_DATE:
            raise CommandError(
                f"Legacy URLs are still registered after {legacy.SUNSET_DATE}; remove them."
            )
