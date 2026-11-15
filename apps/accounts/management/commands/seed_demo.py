from django.core.management.base import BaseCommand

from apps.enquiries.models import Enquiry
from apps.jobs.models import Job
from apps.training.models import Category, Programme

JOBS = [
    {
        "title": "SAP MM Consultant",
        "location": "Irving, TX",
        "employment_type": "contract",
        "description": (
            "We are looking for an SAP MM consultant with hands-on experience in "
            "procurement, inventory management and supplier collaboration.\n\n"
            "You will work with our client teams on implementation and support projects."
        ),
        "requirements": "- 4+ years SAP MM experience\n- S/4HANA exposure preferred\n- Strong communication skills",
        "published": True,
    },
    {
        "title": "Java Developer",
        "location": "Remote",
        "employment_type": "full_time",
        "description": (
            "Build and maintain backend services for our client platform.\n\n"
            "You will design APIs, review code and help shape technical direction."
        ),
        "requirements": "- 3+ years Java/Spring\n- REST and SQL\n- Git-based workflows",
        "published": True,
    },
]

PROGRAMMES = [
    {
        "title": "SAP MM Fundamentals",
        "category": "SAP",
        "duration": "6 weeks",
        "schedule": "Evening batches",
        "description": (
            "Hands-on SAP Materials Management training covering master data, "
            "purchasing and inventory processes."
        ),
        "registration_open": True,
        "published": True,
    },
    {
        "title": "Scrum & Agile Foundations",
        "category": "Scrum & Agile",
        "duration": "4 weeks",
        "description": (
            "Practical Scrum and Agile foundations for teams and individuals "
            "preparing for certification."
        ),
        "registration_open": True,
        "published": True,
    },
]


class Command(BaseCommand):
    help = "Create sample jobs and programmes for demos (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--cleanup",
            action="store_true",
            help="Remove the deployment smoke-test enquiry and QA user instead.",
        )

    def handle(self, *args, **options):
        if options["cleanup"]:
            enquiries = Enquiry.objects.filter(name="Deploy Smoke Test").delete()[0]
            from django.contrib.auth import get_user_model

            qa = get_user_model().objects.filter(email="qa.smoke@example.com").delete()[0]
            self.stdout.write(self.style.SUCCESS(f"Removed {enquiries} enquiry row(s), {qa} QA user(s)."))
            return

        for name in ("SAP", "Scrum & Agile"):
            Category.objects.get_or_create(name=name, defaults={"published": True})

        for data in JOBS:
            Job.objects.get_or_create(title=data["title"], defaults=data)

        for data in PROGRAMMES:
            category = Category.objects.get(name=data["category"])
            fields = {k: v for k, v in data.items() if k != "category"}
            Programme.objects.get_or_create(
                title=data["title"], defaults={**fields, "category": category}
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo content ready: {Job.objects.filter(published=True).count()} live jobs, "
                f"{Programme.objects.filter(published=True).count()} live programmes."
            )
        )
