import io

from django.template.loader import render_to_string
from weasyprint import HTML

from config.constants import COMPANY


def generate_certificate_pdf(registration):
    html = render_to_string(
        "training/certificate.html", {"reg": registration, "COMPANY": COMPANY}
    )
    pdf = io.BytesIO()
    HTML(string=html).write_pdf(pdf)
    return pdf.getvalue()
