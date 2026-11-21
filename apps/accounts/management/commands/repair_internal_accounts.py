from django.core.management.base import BaseCommand

from apps.accounts.models import STAFF_SUBGROUPS, User, sync_access


class Command(BaseCommand):
    help = "Repair internal account flags for admin/staff users. Dry-run by default."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write the repaired flags and groups.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        changes = 0
        for user in User.objects.prefetch_related("groups"):
            group_names = {group.name for group in user.groups.all()}
            subgroup = next(
                (name for name in STAFF_SUBGROUPS if name in group_names), None
            )
            if user.role == User.Role.ADMIN:
                wanted = (True, True)
            elif user.role == User.Role.STAFF and subgroup:
                wanted = (True, False)
            else:
                continue
            is_staff, is_superuser = wanted
            if user.is_staff == is_staff and user.is_superuser == is_superuser:
                continue
            changes += 1
            self.stdout.write(
                f"{user.email}: is_staff {user.is_staff}→{is_staff}, "
                f"is_superuser {user.is_superuser}→{is_superuser}"
            )
            if apply:
                user.is_staff = is_staff
                user.is_superuser = is_superuser
                user.save(update_fields=["is_staff", "is_superuser"])
                sync_access(
                    user, subgroup if user.role == User.Role.STAFF else None
                )
        suffix = "" if apply else " (dry run; pass --apply to write)"
        self.stdout.write(self.style.SUCCESS(f"{changes} account(s) need repair{suffix}."))
