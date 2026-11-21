from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import STAFF_SUBGROUPS, User, sync_access


class Command(BaseCommand):
    help = (
        "Repair admin/staff flags and groups for internal accounts. "
        "Staff without a subgroup are reported and left untouched. Dry-run by default."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write flags/groups. Direct permissions are always cleared for repaired users.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        changes = 0
        skipped = 0

        def repair(user, subgroup):
            nonlocal changes
            expected_group = "Admin" if user.role == User.Role.ADMIN else subgroup
            groups = set(user.groups.values_list("name", flat=True))
            flags_ok = (
                user.is_staff is True
                and user.is_superuser is (user.role == User.Role.ADMIN)
            )
            groups_ok = groups == {expected_group}
            direct_permissions_ok = not user.user_permissions.exists()
            if flags_ok and groups_ok and direct_permissions_ok:
                return
            changes += 1
            self.stdout.write(
                f"{user.email}: flags {user.is_staff}/{user.is_superuser} -> "
                f"{True}/{user.role == User.Role.ADMIN}; groups {sorted(groups)} -> "
                f"{[expected_group]}"
            )
            if apply:
                user.is_staff = True
                user.is_superuser = user.role == User.Role.ADMIN
                user.save(update_fields=["is_staff", "is_superuser"])
                sync_access(user, subgroup)

        with transaction.atomic():
            for user in User.objects.prefetch_related("groups", "user_permissions"):
                if user.role == User.Role.ADMIN:
                    repair(user, None)
                    continue
                if user.role != User.Role.STAFF:
                    continue
                subgroup = next(
                    (name for name in STAFF_SUBGROUPS if name in {g.name for g in user.groups.all()}),
                    None,
                )
                if not subgroup:
                    if user.is_staff:
                        skipped += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"{user.email}: staff without a valid subgroup; left "
                                "unchanged. Assign a subgroup in /manage/users/ first."
                            )
                        )
                    continue
                repair(user, subgroup)

        suffix = "" if apply else " (dry run; pass --apply to write)"
        self.stdout.write(
            self.style.SUCCESS(
                f"{changes} account(s) repaired, {skipped} staff account(s) skipped{suffix}."
            )
        )
