def client_ip(request):
    """The real client IP.

    Cloudflare + Render append several addresses to X-Forwarded-For
    ("client, cloudflare, internal"); the client is always first.
    Django-ratelimit expects a single address, not the raw header.
    """
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
