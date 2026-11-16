from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models


class UserManager(DjangoUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("email_verified", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class AccountType(models.TextChoices):
        CANDIDATE = "candidate", "Candidate"
        STUDENT = "student", "Training Student"

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        SUPERADMIN = "superadmin", "Superadmin"
        CEO = "ceo", "CEO"
        STAFF = "staff", "Staff"

    username = None
    email = models.EmailField("email address", unique=True)
    phone = models.CharField(max_length=40, blank=True)
    account_type = models.CharField(
        max_length=20, choices=AccountType.choices, default=AccountType.CANDIDATE
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STAFF)
    email_verified = models.BooleanField(default=False)

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
        return self.account_type == self.AccountType.CANDIDATE

    @property
    def is_student(self):
        return self.account_type == self.AccountType.STUDENT

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER and self.is_active

    @property
    def is_superadmin(self):
        return self.role == self.Role.SUPERADMIN and self.is_active

    @property
    def is_ceo(self):
        return self.role == self.Role.CEO and self.is_active

    @property
    def is_portal_staff(self):
        return self.is_staff

    @property
    def can_manage_users(self):
        return self.is_superuser or self.role in (self.Role.OWNER, self.Role.SUPERADMIN, self.Role.CEO)

    def assignable_roles(self):
        """(value, label) pairs this account may grant to someone else."""
        if self.role == self.Role.OWNER:
            roles = [self.Role.SUPERADMIN, self.Role.CEO, self.Role.STAFF]
        elif self.role == self.Role.SUPERADMIN:
            roles = [self.Role.CEO, self.Role.STAFF]
        elif self.role == self.Role.CEO:
            roles = [self.Role.STAFF]
        else:
            roles = []
        return [(role.value, role.label) for role in roles]

    def can_manage_account(self, other):
        if other.role == self.Role.OWNER:
            return False
        if self.role == self.Role.OWNER:
            return True
        if self.role == self.Role.SUPERADMIN:
            return other.role != self.Role.SUPERADMIN
        if self.role == self.Role.CEO:
            return other.role == self.Role.STAFF
        return False


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
