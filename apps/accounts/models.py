from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models

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
