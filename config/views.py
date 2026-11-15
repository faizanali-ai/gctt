from django.shortcuts import render


def page(request, template):
    return render(request, f"pages/{template}.html")
