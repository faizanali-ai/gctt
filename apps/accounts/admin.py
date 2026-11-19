from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.exceptions import PermissionDenied
from django.db import transaction

from .models import STAFF_SUBGROUPS, AuditLog, TeamProfile, User, sync_access


def _active_admin_count(lock=False):
    admins = User.objects.select_for_update() if lock else User.objects
    # Fetch ids: PostgreSQL rejects FOR UPDATE combined with COUNT(*).
    return len(
        list(
            admins.filter(
                role=User.Role.ADMIN, is_active=True, is_staff=True
            ).values_list("pk", flat=True)
        )
    )


def _subgroup_for(user):
    """Pick deterministically using STAFF_SUBGROUPS priority, not DB order."""
    names = set(
        user.groups.filter(name__in=STAFF_SUBGROUPS).values_list("name", flat=True)
    )
    return next((name for name in STAFF_SUBGROUPS if name in names), None)


@admin.register(TeamProfile)
class TeamProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "section", "designation", "published", "order")
    list_filter = ("section", "published")
    search_fields = ("name", "designation")
    list_editable = ("published", "order")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "target", "ip")
    list_filter = ("action",)
    search_fields = ("actor__email", "action", "target", "details")
    readonly_fields = ("actor", "action", "target", "details", "ip", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "display_name", "role", "account_type", "email_verified", "is_staff", "date_joined")
    list_filter = ("role", "account_type", "is_staff", "is_superuser", "email_verified")
    search_fields = ("email", "first_name", "last_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal info",
            {"fields": ("first_name", "last_name", "phone", "role", "account_type", "email_verified")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "password1", "password2"),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        with transaction.atomic():
            if change:
                previous = User.objects.get(pk=obj.pk)
                self_downgrade = obj.pk == request.user.pk and (
                    obj.role != User.Role.ADMIN or not obj.is_active
                )
                last_admin = previous.is_admin and (
                    obj.role != User.Role.ADMIN or not obj.is_active
                ) and _active_admin_count(lock=True) <= 1
                if self_downgrade:
                    raise PermissionDenied(
                        "You cannot remove your own admin access."
                    )
                if last_admin:
                    raise PermissionDenied(
                        "You cannot remove the last active admin."
                    )
            super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        with transaction.atomic():
            if obj.pk == request.user.pk:
                raise PermissionDenied("You cannot delete your own account here.")
            if obj.is_admin and _active_admin_count(lock=True) <= 1:
                raise PermissionDenied("You cannot delete the last active admin.")
            super().delete_model(request, obj)

    def has_delete_permission(self, request, obj=None):
        if not super().has_delete_permission(request, obj):
            return False
        if obj is None:
            return True
        if obj.pk == request.user.pk:
            return False
        return not (obj.is_admin and _active_admin_count() <= 1)

    def get_actions(self, request):
        # Bulk delete bypasses delete_model and the last-admin guard.
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        user = form.instance
        with transaction.atomic():
            sync_access(user, _subgroup_for(user))
