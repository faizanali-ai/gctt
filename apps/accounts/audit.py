
from config.ratelimit import client_ip

from .models import AuditLog


def log_action(request, action, target="", details=""):
    AuditLog.objects.create(
        actor=request.user if request.user.is_authenticated else None,
        action=action,
        target=str(target)[:200],
        details=str(details)[:2000],
        ip=client_ip(request),
    )
