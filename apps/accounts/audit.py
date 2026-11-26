import logging

from django.db import transaction

from config.ratelimit import client_ip

from .models import AuditLog

logger = logging.getLogger(__name__)


def log_action(request, action, target="", details=""):
    try:
        with transaction.atomic():
            AuditLog.objects.create(
                actor=request.user if request.user.is_authenticated else None,
                action=action,
                target=str(target)[:200],
                details=str(details)[:2000],
                ip=client_ip(request),
            )
    except Exception:
        # Audit is important, but an audit-table failure must not roll back or
        # 500 a completed business action. The exception is visible in logs.
        logger.exception("Failed to write audit action %s", action)
