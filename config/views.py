from django.http import HttpResponse
from django.shortcuts import render

from apps.accounts.models import TeamProfile


def healthz(request):
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
