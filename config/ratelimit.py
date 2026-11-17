def client_ip(request):
    """The real client IP.

    In production behind Cloudflare, CF-Connecting-IP is set by Cloudflare edge
    and cannot be spoofed by clients sending forged X-Forwarded-For headers.
    In environments without CF-Connecting-IP, fall back to the first address in
    X-Forwarded-For or REMOTE_ADDR.
    """
    cf_ip = request.META.get("HTTP_CF_CONNECTING_IP", "").strip()
    if cf_ip:
        return cf_ip
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "").strip()
