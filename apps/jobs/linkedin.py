import json
import logging
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


def generate_linkedin_post_text(job, request=None):
    base_url = "https://gctekton.com"
    if request:
        base_url = request.build_absolute_uri("/").rstrip("/")
    job_url = f"{base_url}/careers/{job.slug}/"

    text = (
        f"🚀 NEW DIRECT MANDATE: {job.title}\n\n"
        f"📍 Location: {job.location}\n"
        f"💼 Engagement Type: {job.get_employment_type_display()}\n"
        f"🏢 Organization: Global Center for Technology & Training (GCTT)\n\n"
        f"We are actively vetting and placing qualified technical professionals for this enterprise engagement. "
        f"Direct W2 / SOW engagement with verified corporate enterprise partners.\n\n"
        f"👉 Review full mandate requirements and apply directly: {job_url}\n\n"
        f"#TechJobs #Hiring #ITStaffing #EnterpriseTech #Careers #GCTT #Recruitment"
    )
    return text


def generate_linkedin_share_url(job, request=None):
    base_url = "https://gctekton.com"
    if request:
        base_url = request.build_absolute_uri("/").rstrip("/")
    job_url = f"{base_url}/careers/{job.slug}/"
    return f"https://www.linkedin.com/sharing/share-offsite/?url={urllib.parse.quote(job_url)}"


def post_job_to_linkedin(job, request=None):
    """
    Simultaneously post job to LinkedIn Company Page via LinkedIn REST API.
    Requires LINKEDIN_ACCESS_TOKEN and LINKEDIN_ORGANIZATION_ID in settings/env.
    """
    token = getattr(settings, "LINKEDIN_ACCESS_TOKEN", None)
    org_id = getattr(settings, "LINKEDIN_ORGANIZATION_ID", None)

    if not token or not org_id:
        logger.info("LinkedIn API credentials not set. Returning share URL & copy for manual or webhook sync.")
        return {
            "success": False,
            "message": "LinkedIn API credentials (LINKEDIN_ACCESS_TOKEN / LINKEDIN_ORGANIZATION_ID) not configured.",
            "share_url": generate_linkedin_share_url(job, request),
            "post_text": generate_linkedin_post_text(job, request),
        }

    base_url = "https://gctekton.com"
    if request:
        base_url = request.build_absolute_uri("/").rstrip("/")
    job_url = f"{base_url}/careers/{job.slug}/"
    post_text = generate_linkedin_post_text(job, request)

    endpoint = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    payload = {
        "author": f"urn:li:organization:{org_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": post_text
                },
                "shareMediaCategory": "ARTICLE",
                "media": [
                    {
                        "status": "READY",
                        "description": {"text": job.description[:200]},
                        "originalUrl": job_url,
                        "title": {"text": f"{job.title} — GCTT Direct Mandate"},
                    }
                ],
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }

    try:
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            post_id = res_data.get("id", "posted")
            logger.info("Successfully published job %s to LinkedIn Organization %s: %s", job.pk, org_id, post_id)
            return {"success": True, "post_id": post_id, "message": "Successfully posted to LinkedIn Company Page."}
    except Exception as exc:
        logger.exception("Failed to publish job %s to LinkedIn API", job.pk)
        return {
            "success": False,
            "message": f"LinkedIn API error: {exc!s}",
            "share_url": generate_linkedin_share_url(job, request),
            "post_text": post_text,
        }
