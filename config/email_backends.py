import base64
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

# Cloudflare in front of api.resend.com rejects the default urllib User-Agent
# with HTTP 403 error 1010 (browser_signature_banned), so identify the app.
USER_AGENT = "GCTT-Mailer/1.0 (+https://gctekton.com)"


class ResendEmailBackend(BaseEmailBackend):
    """Send Django email through Resend's HTTPS API.

    Render's free web services block outbound SMTP ports 25, 465 and 587, so
    the SMTP backend cannot work there. HTTPS is not blocked.
    """

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.api_key = getattr(settings, "RESEND_API_KEY", "").strip()
        self.api_url = getattr(
            settings, "RESEND_API_URL", "https://api.resend.com/emails"
        )
        self.timeout = float(getattr(settings, "EMAIL_TIMEOUT", 10))

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        if not self.api_key:
            if not self.fail_silently:
                raise ImproperlyConfigured("RESEND_API_KEY is not configured")
            return 0

        sent = 0
        for message in email_messages:
            try:
                self._send(message)
                sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
                logger.exception("Failed to send email through Resend")
        return sent

    def _send(self, message):
        html_body = next(
            (
                content
                for content, content_type in message.alternatives
                if content_type == "text/html"
            ),
            None,
        )
        payload = {
            "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
            "to": list(message.to),
            "subject": message.subject,
            "text": message.body,
        }
        if html_body:
            payload["html"] = html_body
        if message.cc:
            payload["cc"] = list(message.cc)
        if message.bcc:
            payload["bcc"] = list(message.bcc)
        if message.reply_to:
            payload["reply_to"] = list(message.reply_to)
        if message.extra_headers:
            payload["headers"] = dict(message.extra_headers)
        if message.attachments:
            payload["attachments"] = [
                {
                    "filename": filename,
                    "content": base64.b64encode(content).decode("ascii"),
                }
                for filename, content, _mimetype in message.attachments
            ]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        idempotency_key = getattr(message, "idempotency_key", "")
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        request = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(
                f"Resend API returned HTTP {exc.code}: {detail}"
            ) from exc
