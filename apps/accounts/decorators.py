from functools import wraps

from django.core.exceptions import PermissionDenied


def staff_required(view):
    """Require an active internal account. Role permissions still apply."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        user = request.user
        if not (user.is_authenticated and user.is_active and user.is_staff):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper
