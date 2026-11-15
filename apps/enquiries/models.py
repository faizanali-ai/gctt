from django.db import models


class Enquiry(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    class Category(models.TextChoices):
        IT_STAFFING = "it_staffing", "IT Staffing"
        RECRUITMENT = "recruitment", "Recruitment"
        TALENT_ACQUISITION = "talent_acquisition", "Talent Acquisition"
        TRAINING = "training", "Training & Development"
        CAREER_RESTART = "career_restart", "Career Restart"
        EMPLOYER_INTAKE = "employer_intake", "Employer Talent Request"
        GENERAL = "general", "General Enquiry"

    name = models.CharField(max_length=120)
    email = models.EmailField(max_length=200)
    phone = models.CharField(max_length=40, blank=True)
    company = models.CharField(max_length=120, blank=True)
    area = models.CharField(
        max_length=40,
        blank=True,
        choices=[
            ("SAP", "SAP"),
            ("Scrum & Agile", "Scrum & Agile"),
            ("Other IT role", "Other IT role"),
        ],
    )
    how_heard = models.CharField(
        max_length=40,
        blank=True,
        choices=[
            ("Google", "Google"),
            ("LinkedIn", "LinkedIn"),
            ("Referral", "Referral"),
            ("Direct", "Direct"),
            ("Other", "Other"),
        ],
    )
    category = models.CharField(
        max_length=30, choices=Category.choices, default=Category.GENERAL
    )
    message = models.TextField(max_length=4000)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "enquiries"

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"
