from django.db import DatabaseError, connection
from django.http import HttpResponse
from django.shortcuts import render

from apps.accounts.models import PageContent, PageFAQ, TeamProfile


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


def page_context(slug):
    try:
        content = PageContent.objects.filter(page_slug=slug).first()
        faqs = list(
            PageFAQ.objects.filter(page_slug=slug, is_published=True).order_by("order", "id")
        )
        return {
            "page_content": content,
            "page_faqs": faqs,
        }
    except DatabaseError:
        return {"page_content": None, "page_faqs": []}


def page(request, template):
    ctx = page_context(template)
    return render(request, f"pages/{template}.html", ctx)


def about(request):
    profiles = TeamProfile.objects.filter(published=True)
    ctx = page_context("about")
    ctx.update(
        {
            "team": profiles.filter(section=TeamProfile.Section.TEAM),
            "network": profiles.filter(section=TeamProfile.Section.NETWORK),
        }
    )
    return render(request, "pages/about.html", ctx)
