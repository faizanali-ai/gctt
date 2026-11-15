from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from .forms import RegistrationForm
from .models import Programme


def programme_list(request):
    programmes = Programme.objects.filter(published=True).select_related("category")
    return render(request, "training/programme_list.html", {"programmes": programmes})


def programme_detail(request, slug):
    programme = get_object_or_404(Programme, slug=slug, published=True)
    registered = (
        request.user.is_authenticated
        and programme.registrations.filter(student=request.user).exists()
    )
    return render(
        request,
        "training/programme_detail.html",
        {"programme": programme, "form": RegistrationForm(), "registered": registered},
    )


@require_POST
@login_required
@ratelimit(key="user", rate="20/h", method="POST", block=True)
def programme_register(request, slug):
    programme = get_object_or_404(Programme, slug=slug, published=True)
    if not programme.registration_open:
        messages.error(request, "Registration for this programme is closed.")
        return redirect("programme_detail", slug=programme.slug)
    form = RegistrationForm(request.POST)
    if form.is_valid():
        registration = form.save(commit=False)
        registration.programme = programme
        registration.student = request.user
        try:
            with transaction.atomic():
                registration.save()
            messages.success(request, "Your registration has been sent.")
        except IntegrityError:
            messages.error(request, "You are already registered for this programme.")
        return redirect("programme_detail", slug=programme.slug)
    return render(
        request,
        "training/programme_detail.html",
        {"programme": programme, "form": form, "registered": False},
    )


def sap_scrum(request):
    programmes = Programme.objects.filter(
        published=True, category__name__in=["SAP", "Scrum & Agile"]
    ).select_related("category")
    return render(request, "pages/sap_scrum.html", {"programmes": programmes})
