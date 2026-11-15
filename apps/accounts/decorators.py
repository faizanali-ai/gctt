from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def employer_required(view):
    @wraps(view)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_employer:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return _wrapped
