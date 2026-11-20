from django.apps import AppConfig
from django.db.models.signals import post_migrate

ROLE_PERMISSIONS = {
    "Recruiter": [
        ("jobs", "job", ["view", "add", "change"]),
        ("jobs", "application", ["view", "change"]),
    ],
    "Trainer": [
        ("training", "category", ["view", "add", "change"]),
        ("training", "programme", ["view", "add", "change"]),
        ("training", "registration", ["view", "change"]),
    ],
    "Enquiry Manager": [
        ("enquiries", "enquiry", ["view", "change"]),
    ],
    "Admin": [
        ("jobs", "job", ["view", "add", "change", "delete"]),
        ("jobs", "application", ["view", "change", "delete"]),
        ("training", "category", ["view", "add", "change", "delete"]),
        ("training", "programme", ["view", "add", "change", "delete"]),
        ("training", "registration", ["view", "change", "delete"]),
        ("enquiries", "enquiry", ["view", "change", "delete"]),
    ],
}


def assign_permissions(label=None):
    """Assign role permissions. With a label, only that app's models (called per post_migrate)."""
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType

    for role, specs in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=role)
        permissions = set()
        for app_label, model, actions in specs:
            if label and app_label != label:
                continue
            content_type = ContentType.objects.filter(app_label=app_label, model=model).first()
            if content_type is None:
                continue
            permissions.update(
                Permission.objects.filter(
                    content_type=content_type,
                    codename__in=[f"{action}_{model}" for action in actions],
                )
            )
        if label:
            permissions.update(group.permissions.all())
        group.permissions.set(permissions)


def sync_role_groups(sender, **kwargs):
    assign_permissions(getattr(sender, "label", None))


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"

    def ready(self):
        post_migrate.connect(sync_role_groups, dispatch_uid="accounts.sync_role_groups")
        from django.contrib import admin

        def admin_only_permission(request):
            user = request.user
            return bool(
                user
                and user.is_authenticated
                and user.is_active
                and user.is_staff
                and user.is_superuser
                and getattr(user, "role", "") == "admin"
            )

        admin.site.has_permission = admin_only_permission
