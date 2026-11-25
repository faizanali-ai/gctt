import fcntl
import io
import tempfile
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from weasyprint import HTML

from config.site import company


def generate_certificate_pdf(registration):
    """Render a certificate PDF under a cross-process lock to cap memory usage."""
    html = render_to_string(
        "training/certificate.html",
        {"reg": registration, "COMPANY": company()},
    )
    pdf = io.BytesIO()
    base_url = (settings.BASE_DIR / "static").as_uri() + "/"
    lock_path = Path(tempfile.gettempdir()) / "gctt-weasyprint.lock"
    with open(lock_path, "a+") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            HTML(string=html, base_url=base_url).write_pdf(pdf)
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    return pdf.getvalue()
