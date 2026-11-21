import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from config.emails import send_promotional


class Command(BaseCommand):
    help = (
        "Preview or send a promotional email to users who explicitly opted in. "
        "Dry-run by default; pass --send to deliver."
    )

    def add_arguments(self, parser):
        parser.add_argument("--subject", required=True)
        parser.add_argument(
            "--body-file",
            required=True,
            help="Plain-text campaign body. The HTML version wraps the same text.",
        )
        parser.add_argument(
            "--send",
            action="store_true",
            help="Actually send. Without this flag the command only previews.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Maximum recipients in this run (default 50).",
        )
        parser.add_argument(
            "--after-id",
            type=int,
            default=0,
            help="Resume after this user ID (printed by the previous run).",
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=1.0,
            help="Seconds between messages (default 1).",
        )

    def handle(self, *args, **options):
        if options["limit"] < 1:
            raise CommandError("--limit must be at least 1")
        if options["after_id"] < 0:
            raise CommandError("--after-id cannot be negative")
        if options["sleep"] < 0:
            raise CommandError("--sleep cannot be negative")
        if not options["subject"].strip():
            raise CommandError("--subject cannot be empty")
        body_path = Path(options["body_file"])
        try:
            content = body_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise CommandError(f"Could not read --body-file: {exc}") from exc
        if not content:
            raise CommandError("--body-file is empty")

        base = User.objects.filter(is_active=True, promotional_opt_in=True)
        total = base.count()
        recipients = list(
            base.filter(pk__gt=options["after_id"]).order_by("pk")[
                : options["limit"]
            ]
        )
        self.stdout.write(
            f"Opted-in recipients: {total}; starting after ID {options['after_id']}; "
            f"limit this run: {options['limit']}"
        )
        if not recipients:
            self.stdout.write("No recipients remain.")
            return
        if not options["send"]:
            self.stdout.write(
                f"Dry run; would send to {len(recipients)} recipient(s); "
                "pass --send to deliver."
            )
            return

        sent = 0
        failed = 0
        last_successful_id = options["after_id"]
        for user in recipients:
            if send_promotional(user, options["subject"], content.strip()):
                sent += 1
                last_successful_id = user.pk
            else:
                failed += 1
                break
            if options["sleep"]:
                time.sleep(options["sleep"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Sent {sent} promotional email(s); {failed} failed. "
                f"Next --after-id: {last_successful_id}."
            )
        )
        remaining = base.filter(pk__gt=last_successful_id).count()
        if failed:
            self.stdout.write(
                self.style.WARNING(
                    "Stopped after a send failure. Re-run with the same "
                    f"--after-id {last_successful_id} to retry the failed recipient."
                )
            )
        elif remaining:
            self.stdout.write(
                self.style.WARNING(
                    f"{remaining} recipient(s) remain. Run again on another day "
                    "to stay within the provider limit."
                )
            )
