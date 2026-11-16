from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AuditLog, TeamProfile, User


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
