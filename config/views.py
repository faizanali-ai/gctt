from django.db import DatabaseError, connection
from django.http import HttpResponse
from django.shortcuts import render

from apps.accounts.models import TeamProfile


def wake(request):
    """Liveness endpoint with no database dependency (Render/keepalive target)."""
    return HttpResponse("ok", content_type="text/plain")


def healthz(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return HttpResponse("database unavailable", status=503, content_type="text/plain")
    return HttpResponse("ok", content_type="text/plain")


def page(request, template):
    return render(request, f"pages/{template}.html")


def about(request):
    profiles = TeamProfile.objects.filter(published=True)
    return render(
        request,
        "pages/about.html",
        {
            "team": profiles.filter(section=TeamProfile.Section.TEAM),
            "network": profiles.filter(section=TeamProfile.Section.NETWORK),
        },
    )
