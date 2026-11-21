import io

from django.conf import settings
from django.template.loader import render_to_string
from weasyprint import HTML

from config.site import company


def generate_certificate_pdf(registration):
    html = render_to_string(
        "training/certificate.html",
        {"reg": registration, "COMPANY": company()},
    )
    pdf = io.BytesIO()
    base_url = (settings.BASE_DIR / "static").as_uri() + "/"
    HTML(string=html, base_url=base_url).write_pdf(pdf)
    return pdf.getvalue()
