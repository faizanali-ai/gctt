import uuid

from django.conf import settings
from django.db import IntegrityError, models, transaction
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    published = models.BooleanField(default=False, db_index=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Programme(models.Model):
    class DeliveryMode(models.TextChoices):
        ONLINE = "online", "Online"
        IN_PERSON = "in_person", "In-person"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="programmes"
    )
    delivery_mode = models.CharField(
        max_length=20, choices=DeliveryMode.choices, default=DeliveryMode.ONLINE
    )
    schedule = models.CharField(max_length=200, blank=True)
    duration = models.CharField(max_length=100, blank=True)
    image_url = models.URLField(blank=True)  # Legacy; not rendered by the public design.
    description = models.TextField()
    registration_open = models.BooleanField(default=False)
    published = models.BooleanField(default=False, db_index=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "-created_at"]

    def save(self, *args, **kwargs):
        generated = not self.slug
        base = slugify(self.title)[:200] or "programme"
        if generated:
            slug, n = base, 1
            while Programme.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base}-{n}"
            self.slug = slug
        try:
            with transaction.atomic():
                super().save(*args, **kwargs)
        except IntegrityError:
            if not generated:
                raise
            self.slug = f"{base}-{uuid.uuid4().hex[:6]}"
            with transaction.atomic():
                super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Registration(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        COMPLETED = "completed", "Completed"

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name="registrations")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="registrations"
    )
    message = models.TextField(max_length=4000, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SUBMITTED, db_index=True
    )
    certificate_issued = models.BooleanField(default=False)
    certificate_ref = models.CharField(max_length=100, unique=True, null=True, blank=True)
    certificate_issued_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["programme", "student"], name="one_registration_per_programme")
        ]

    def __str__(self):
        return f"{self.student} → {self.programme}"

    def issue_certificate(self):
        from django.utils import timezone

        if not self.certificate_ref:
            self.certificate_ref = f"GCTT-{uuid.uuid4().hex[:16].upper()}"
        self.certificate_issued = True
        self.certificate_issued_at = timezone.now()
        self.save(update_fields=["certificate_issued", "certificate_ref", "certificate_issued_at"])

    def revoke_certificate(self):
        self.certificate_issued = False
        self.certificate_ref = None
        self.certificate_issued_at = None
        self.save(update_fields=["certificate_issued", "certificate_ref", "certificate_issued_at"])


class PendingRegistration(models.Model):
    programme = models.ForeignKey(
        Programme, on_delete=models.CASCADE, related_name="pending_registrations"
    )
    email = models.EmailField(max_length=200)
    message = models.TextField(max_length=4000, blank=True)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} → {self.programme}"
