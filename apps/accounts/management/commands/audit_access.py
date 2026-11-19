from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts.models import STAFF_SUBGROUPS


class Command(BaseCommand):
    help = "Read-only audit of internal access levels, groups and direct permissions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Exit nonzero when access issues are found.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        users = list(
            User.objects.prefetch_related("groups", "user_permissions").order_by("email")
        )
        staff_groups = set(STAFF_SUBGROUPS)
        issues = []

        def add(section, message):
            issues.append((section, message))

        admins = [u for u in users if u.role == "admin"]
        active_admins = [u for u in admins if u.is_active and u.is_staff]
        staff = [u for u in users if u.is_staff and u.role == "staff"]
        external = [u for u in users if not u.is_staff]
        candidates = [
            u for u in external if u.account_type == User.AccountType.CANDIDATE
        ]
        students = [u for u in external if u.account_type == User.AccountType.STUDENT]

        subgroup_counts = {name: 0 for name in STAFF_SUBGROUPS}
        for user in staff:
            names = {group.name for group in user.groups.all()}
            for name in names & staff_groups:
                subgroup_counts[name] += 1

        for user in admins:
            names = {group.name for group in user.groups.all()}
            if not user.is_staff:
                add("Administrators", f"{user.email}: role=admin but is_staff=False")
            if not user.is_superuser:
                add("Administrators", f"{user.email}: role=admin but is_superuser=False")
            if "Admin" not in names:
                add("Administrators", f"{user.email}: missing Admin group")
            if names & staff_groups:
                add(
                    "Administrators",
                    f"{user.email}: also in staff subgroup(s) {sorted(names & staff_groups)}",
                )

        for user in staff:
            names = {group.name for group in user.groups.all()}
            subgroups = names & staff_groups
            if not subgroups:
                add("Staff", f"{user.email}: no staff subgroup")
            if len(subgroups) > 1:
                add("Staff", f"{user.email}: multiple subgroups {sorted(subgroups)}")
            extra = names - staff_groups
            if extra:
                add("Staff", f"{user.email}: unexpected groups {sorted(extra)}")
            if user.is_superuser:
                add("Staff", f"{user.email}: is_superuser=True")
            if user.user_permissions.all():
                add("Staff", f"{user.email}: direct user permissions present")

        for user in external:
            names = {group.name for group in user.groups.all()}
            if names:
                add("External users", f"{user.email}: groups {sorted(names)}")
            if user.user_permissions.all():
                add("External users", f"{user.email}: direct user permissions present")
            if user.is_superuser:
                add("External users", f"{user.email}: is_superuser=True")
            if user.account_type not in (
                User.AccountType.CANDIDATE,
                User.AccountType.STUDENT,
            ):
                add("External users", f"{user.email}: invalid account_type")

        for user in users:
            if user.role not in (User.Role.ADMIN, User.Role.STAFF):
                add("Roles", f"{user.email}: invalid role={user.role!r}")

        if not active_admins:
            add("Administrators", "No active admin account exists")

        self.stdout.write(self.style.MIGRATE_HEADING("Access audit"))
        self.stdout.write(
            f"Admins: {len(active_admins)} active / {len(admins)} total"
        )
        self.stdout.write(
            "Staff: "
            + ", ".join(f"{name}={count}" for name, count in subgroup_counts.items())
            + f" (total={len(staff)})"
        )
        self.stdout.write(f"Candidates: {len(candidates)}")
        self.stdout.write(f"Students: {len(students)}")

        if issues:
            self.stdout.write(self.style.ERROR(f"Issues: {len(issues)}"))
            for section in dict.fromkeys(section for section, _ in issues):
                self.stdout.write(self.style.ERROR(f"{section}:"))
                for issue_section, message in issues:
                    if issue_section == section:
                        self.stdout.write(f"  - {message}")
        else:
            self.stdout.write(self.style.SUCCESS("No access issues found."))

        if settings.REQUIRE_STAFF_2FA:
            confirmed = set(
                TOTPDevice.objects.filter(confirmed=True, user__is_staff=True)
                .values_list("user_id", flat=True)
            )
            pending = [
                user
                for user in users
                if user.is_staff and user.is_active and user.pk not in confirmed
            ]
            if pending:
                self.stdout.write(
                    self.style.WARNING(
                        "2FA enrollment pending: "
                        + ", ".join(user.email for user in pending)
                    )
                )

        if options["strict"] and issues:
            raise CommandError(f"Access audit found {len(issues)} issue(s).")
