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

    username = None
    email = models.EmailField("email address", unique=True)
    phone = models.CharField(max_length=40, blank=True)
    account_type = models.CharField(
        max_length=20, choices=AccountType.choices, default=AccountType.CANDIDATE
    )
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
