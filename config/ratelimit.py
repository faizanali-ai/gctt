def client_ip(request):
    """Return the client address supplied by the Render edge.

    Render documents that it sets the first ``X-Forwarded-For`` entry to the
    real client IP. Later entries can be client-supplied, so they are ignored.
    There is no Cloudflare proxy in front of the origin, so CF-Connecting-IP is
    deliberately ignored: a client can forge it.
    """
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        candidate = forwarded.split(",")[0].strip()
        if candidate:
            return candidate[:45]
    return request.META.get("REMOTE_ADDR", "").strip()[:45]
