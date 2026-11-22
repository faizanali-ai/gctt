import uuid
from pathlib import Path

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models, transaction

from config.constants import COMPANY

STAFF_SUBGROUPS = ("Recruiter", "Trainer", "Enquiry Manager")

DESIGNATION_CHOICES = (
    ("admin", "Admin"),
    ("staff", "Staff"),
    ("candidate", "Candidate"),
    ("student", "Training Student"),
)


class UserManager(DjangoUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields["role"] = self.model.Role.ADMIN
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("email_verified", True)
        user = self.create_user(email, password, **extra_fields)
        sync_access(user)
        return user


class User(AbstractUser):
    class AccountType(models.TextChoices):
        CANDIDATE = "candidate", "Candidate"
        STUDENT = "student", "Training Student"

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        STAFF = "staff", "Staff"

    username = None
    email = models.EmailField("email address", unique=True)
    phone = models.CharField(max_length=40, blank=True)
    job_title = models.CharField(max_length=120, blank=True)
    account_type = models.CharField(
        max_length=20, choices=AccountType.choices, default=AccountType.CANDIDATE
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STAFF)
    email_verified = models.BooleanField(default=False)
    welcome_email_sent_at = models.DateTimeField(null=True, blank=True)
    promotional_opt_in = models.BooleanField(default=False)
    promotional_opt_in_at = models.DateTimeField(null=True, blank=True)
    promotional_opt_in_requested_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def display_name(self):
        return self.get_full_name() or self.email

    @property
    def is_candidate(self):
        return not self.is_staff and self.account_type == self.AccountType.CANDIDATE

    @property
    def is_student(self):
        return not self.is_staff and self.account_type == self.AccountType.STUDENT

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN and self.is_active and self.is_staff

    @property
    def designation(self):
        """The account label shown in the portal and user directory."""
        if self.role == self.Role.ADMIN:
            return self.Role.ADMIN.label
        if self.is_staff:
            return self.Role.STAFF.label
        return self.get_account_type_display()

    @property
    def designation_value(self):
        if self.role == self.Role.ADMIN:
            return "admin"
        if self.is_staff:
            return "staff"
        return self.account_type

    @property
    def is_portal_staff(self):
        return self.is_staff

    @property
    def requires_email_otp(self):
        """Every staff account and every role=admin account requires OTP."""
        return self.is_staff or self.role == self.Role.ADMIN

    @property
    def can_manage_users(self):
        return self.is_admin

    def assignable_roles(self):
        """(value, label) pairs this account may grant to someone else."""
        if self.is_admin:
            return [
                (self.Role.ADMIN.value, self.Role.ADMIN.label),
                (self.Role.STAFF.value, self.Role.STAFF.label),
            ]
        return []

    def can_manage_account(self, other):
        return self.is_admin

    def apply_designation(self, designation, subgroup=None):
        """Persist a portal designation and synchronise access flags/groups."""
        if designation == "admin":
            self.role = self.Role.ADMIN
            self.is_staff = True
            self.is_superuser = True
        elif designation == "staff":
            self.role = self.Role.STAFF
            self.is_staff = True
            self.is_superuser = False
        elif designation in ("candidate", "student"):
            self.role = self.Role.STAFF
            self.account_type = (
                self.AccountType.CANDIDATE
                if designation == "candidate"
                else self.AccountType.STUDENT
            )
            self.is_staff = False
            self.is_superuser = False
        else:
            raise ValueError(f"Unknown designation: {designation}")
        with transaction.atomic():
            self.save()
            sync_access(self, subgroup if designation == "staff" else None)
        return self


def sync_access(user, subgroup=None):
    """Apply the role's flags and exactly one permission group.

    Staff must supply one of STAFF_SUBGROUPS. No subgroup means no access,
    which is safe and visible to an administrator.
    """
    from django.contrib.auth.models import Group

    if user.role == User.Role.ADMIN:
        user.is_staff = True
        user.is_superuser = True
        group = Group.objects.get_or_create(name="Admin")[0]
    elif user.is_staff:
        user.is_superuser = False
        group = (
            Group.objects.get_or_create(name=subgroup)[0]
            if subgroup in STAFF_SUBGROUPS
            else None
        )
    else:
        user.is_superuser = False
        group = None

    user.save(update_fields=["is_staff", "is_superuser"])
    user.groups.set([group] if group else [])
    # Groups are the single source of truth; never leave direct permissions behind.
    user.user_permissions.clear()
    return user


class SiteSettings(models.Model):
    """Editable company identity, contact details and home-hero copy."""

    company_name = models.CharField(max_length=120, default=COMPANY["name"])
    legal_name = models.CharField(max_length=160, default=COMPANY["legal_name"])
    tagline = models.CharField(max_length=200, default=COMPANY["tagline"])
    email = models.EmailField(default=COMPANY["email"])
    jobs_email = models.EmailField(default=COMPANY["jobs_email"])
    address = models.CharField(max_length=255, default=COMPANY["address"])
    url = models.URLField(default=COMPANY["url"])
    hero_eyebrow = models.CharField(
        max_length=120, default="Irving, Texas · E-Verify employer"
    )
    hero_title = models.CharField(
        max_length=200, default="Technology talent and training for enterprise teams."
    )
    hero_subtitle = models.TextField(
        blank=True,
        default=(
            "GCTT places technology practitioners with client teams and trains the "
            "people who want to join them. Two divisions, one standard of delivery."
        ),
    )
    hero_cta_label = models.CharField(max_length=60, default="Request talent")
    hero_cta_url = models.CharField(max_length=200, default="/employers/")
    phone = models.CharField(max_length=40, default=COMPANY.get("phone", "+1 (786) 855-8859"), blank=True)
    phone_raw = models.CharField(max_length=40, default=COMPANY.get("phone_raw", "+17868558859"), blank=True)
    announcement_banner_enabled = models.BooleanField(default=False)
    announcement_banner_text = models.CharField(max_length=255, blank=True)
    announcement_banner_link = models.CharField(max_length=200, blank=True)
    allow_candidate_applications = models.BooleanField(default=True)
    allow_student_registrations = models.BooleanField(default=True)
    logo_light_url = models.CharField(max_length=255, blank=True)
    logo_dark_url = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "site settings"
        verbose_name_plural = "site settings"

    def __str__(self):
        return "Site settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        kwargs.pop("force_insert", None)
        # A second unsaved instance must update, or the pk unique index rejects it.
        if self._state.adding and type(self).objects.filter(pk=1).exists():
            kwargs["force_update"] = True
        super().save(*args, **kwargs)
        from config.site import clear_company_cache

        clear_company_cache()

    @classmethod
    def load(cls):
        """Return the singleton, or an unsaved row carrying the defaults."""
        return cls.objects.filter(pk=1).first() or cls()


class EmailOTP(models.Model):
    email = models.EmailField(db_index=True)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["email", "created_at"])]

    def __str__(self):
        return f"{self.email} OTP"


class TeamProfile(models.Model):
    class Section(models.TextChoices):
        TEAM = "team", "Team"
        NETWORK = "network", "Network"

    section = models.CharField(max_length=20, choices=Section.choices, default=Section.TEAM)
    name = models.CharField(max_length=120)
    designation = models.CharField(max_length=120, blank=True)
    bio = models.TextField(blank=True)
    linkedin_url = models.URLField(blank=True)
    # shortcut: photo as URL instead of upload; switch to ImageField + R2 at deploy
    photo_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)
    published = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["section", "order", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_section_display()})"


class AuditLog(models.Model):
    actor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_entries"
    )
    action = models.CharField(max_length=80, db_index=True)
    target = models.CharField(max_length=200, blank=True)
    details = models.TextField(blank=True)
    ip = models.CharField(max_length=45, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "audit log entry"

    def __str__(self):
        return f"{self.actor or 'system'} · {self.action} · {self.target}"


PAGE_CHOICES = (
    ("home", "Home"),
    ("about", "About Us"),
    ("services", "Services / Talent Solutions"),
    ("it_staffing", "IT Staffing"),
    ("recruitment", "Recruitment"),
    ("talent_acquisition", "Talent Acquisition"),
    ("sap_scrum", "SAP & Scrum / Academy"),
    ("career_restart", "Career Restart"),
    ("employers", "For Employers"),
    ("contact", "Contact Us"),
    ("privacy", "Privacy Policy"),
    ("terms", "Terms of Service"),
)

MENU_CHOICES = (
    ("header", "Header Navigation"),
    ("footer_talent", "Footer: Talent Solutions"),
    ("footer_academy", "Footer: Academy"),
    ("footer_company", "Footer: Company"),
    ("footer_legal", "Footer: Legal & Policy"),
)


class PageContent(models.Model):
    """Dynamic, owner-editable page content for each website page."""

    page_slug = models.CharField(max_length=60, unique=True, db_index=True, choices=PAGE_CHOICES)
    title = models.CharField(max_length=200, blank=True, help_text="Browser title / meta title")
    meta_description = models.TextField(blank=True, help_text="Search engine meta description")
    hero_eyebrow = models.CharField(max_length=120, blank=True)
    hero_title = models.CharField(max_length=200, blank=True)
    hero_subtitle = models.TextField(blank=True)
    hero_cta_label = models.CharField(max_length=60, blank=True)
    hero_cta_url = models.CharField(max_length=200, blank=True)
    sections_data = models.JSONField(
        default=dict, blank=True, help_text="Structured page sections (JSON)"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "page content"
        verbose_name_plural = "page content"
        ordering = ["page_slug"]

    def __str__(self):
        return f"Page: {self.get_page_slug_display() or self.page_slug}"


class PageFAQ(models.Model):
    """Owner-managed FAQs displayed on relevant pages."""

    page_slug = models.CharField(
        max_length=60, db_index=True, choices=PAGE_CHOICES, default="home"
    )
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "page FAQ"
        verbose_name_plural = "page FAQs"
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.question} ({self.page_slug})"


class NavigationItem(models.Model):
    """Owner-managed navigation links in header and footer."""

    menu = models.CharField(max_length=30, choices=MENU_CHOICES, default="header", db_index=True)
    label = models.CharField(max_length=80)
    url = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True, db_index=True)
    open_in_new_tab = models.BooleanField(default=False)

    class Meta:
        verbose_name = "navigation item"
        verbose_name_plural = "navigation items"
        ordering = ["menu", "order", "id"]

    def __str__(self):
        return f"{self.label} -> {self.url} ({self.get_menu_display()})"

    def save(self, *args, **kwargs):
        result = super().save(*args, **kwargs)
        from config.context_processors import clear_navigation_cache

        clear_navigation_cache()
        return result

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        from config.context_processors import clear_navigation_cache

        clear_navigation_cache()
        return result


def media_upload_to(instance, filename):
    # Opaque UUID filenames: prevents S3 overwrite collisions and directory enumeration.
    ext = Path(filename).suffix.lower()[:10]
    return f"media/{uuid.uuid4().hex}{ext}"


class MediaAsset(models.Model):
    """Uploaded marketing media, logos, and documents."""

    title = models.CharField(max_length=160)
    file = models.FileField(upload_to=media_upload_to)
    alt_text = models.CharField(max_length=200, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "media asset"
        verbose_name_plural = "media assets"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title

    @property
    def is_image(self) -> bool:
        if not self.file:
            return False
        import os
        ext = os.path.splitext(self.file.name)[1].lower()
        return ext in {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".avif", ".ico"}

    @property
    def public_url(self) -> str:
        from django.urls import reverse
        return reverse("media_asset_serve", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, "size") and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)

