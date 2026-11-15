
from .models import AuditLog


def log_action(request, action, target="", details=""):
    AuditLog.objects.create(
        actor=request.user if request.user.is_authenticated else None,
        action=action,
        target=str(target)[:200],
        details=str(details)[:2000],
        ip=(
            request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR", "")
        )[:45],
    )
