import logging
import uuid
from pathlib import Path

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.text import slugify

logger = logging.getLogger(__name__)


def resume_upload_to(instance, filename):
    # Opaque filenames: resumes are private and never guessable.
    suffix = Path(filename).suffix.lower()[:10]
    return f"resumes/{uuid.uuid4().hex}{suffix}"


class Job(models.Model):
    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", "Full-time"
        PART_TIME = "part_time", "Part-time"
        CONTRACT = "contract", "Contract"
        INTERNSHIP = "internship", "Internship"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    location = models.CharField(max_length=200)
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME
    )
    description = models.TextField()
    requirements = models.TextField(blank=True)
    published = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200] or "job"
            slug, n = base, 1
            while Job.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base}-{n}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Application(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        SHORTLISTED = "shortlisted", "Shortlisted"
        REJECTED = "rejected", "Rejected"
        SELECTED = "selected", "Selected"

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications"
    )
    resume = models.FileField(
        upload_to=resume_upload_to,
        validators=[FileExtensionValidator(["pdf", "doc", "docx"])],
    )
    message = models.TextField(max_length=4000, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SUBMITTED, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["job", "applicant"], name="one_application_per_job_user")
        ]

    def __str__(self):
        return f"{self.applicant} → {self.job}"


class PendingApplication(models.Model):
    job = models.ForeignKey(
        Job, on_delete=models.CASCADE, related_name="pending_applications"
    )
    email = models.EmailField(max_length=200)
    resume = models.FileField(
        upload_to=resume_upload_to,
        validators=[FileExtensionValidator(["pdf", "doc", "docx"])],
    )
    message = models.TextField(max_length=4000, blank=True)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} → {self.job}"


@receiver(post_delete, sender=Application)
def delete_resume_file(sender, instance, **kwargs):
    if instance.resume:
        try:
            instance.resume.delete(save=False)
        except OSError:
            logger.warning(
                "Failed to remove resume file %s on application delete", instance.resume.name
            )

