from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.enquiries.models import Enquiry
from apps.jobs.models import Job
from apps.training.models import Category, Programme

JOBS = [
    {
        "title": "SAP MM Consultant",
        "location": "Irving, TX",
        "employment_type": "contract",
        "description": (
            "GCTT is deploying an experienced SAP S/4HANA Materials Management (MM) Consultant "
            "for an enterprise supply chain modernization initiative in Irving, TX.\n\n"
            "You will spearhead procurement process configuration, inventory valuation models, "
            "automated MRP scheduling, and cross-functional integration with FICO and SD ledgers."
        ),
        "requirements": (
            "- 4+ years of hands-on SAP MM configuration and enterprise delivery experience\n"
            "- Direct S/4HANA migration or greenfield implementation exposure\n"
            "- Deep proficiency in Procure-to-Pay (P2P), inventory management, and EDI/IDoc workflows\n"
            "- Exceptional stakeholder communication and cross-functional alignment skills"
        ),
        "published": True,
    },
    {
        "title": "Java Developer",
        "location": "Remote",
        "employment_type": "full_time",
        "description": (
            "Build and scale mission-critical cloud-native distributed microservices for an enterprise partner.\n\n"
            "You will design high-throughput RESTful and event-driven APIs, architect resilient PostgreSQL schemas, "
            "conduct rigorous architectural code reviews, and drive cloud infrastructure reliability."
        ),
        "requirements": (
            "- 3+ years of production experience with Java 17+, Spring Boot, and microservices architecture\n"
            "- Strong relational database modeling, indexing, and query optimization (PostgreSQL/SQL)\n"
            "- Practical containerization experience with Docker, Kubernetes, and automated CI/CD pipelines\n"
            "- Firm grasp of asynchronous messaging paradigms (Kafka/RabbitMQ) and API security standards"
        ),
        "published": True,
    },
]

PROGRAMMES = [
    {
        "title": "SAP MM Fundamentals",
        "category": "SAP",
        "duration": "6 weeks",
        "schedule": "Evening & Weekend Batches",
        "description": (
            "Comprehensive, hands-on enterprise workforce accelerator in SAP S/4HANA Materials Management. "
            "Covers master data governance, purchasing configurations, inventory valuation, MRP algorithms, and "
            "live enterprise sandbox simulations. Culminates in a tamper-evident verifiable digital credential."
        ),
        "registration_open": True,
        "published": True,
    },
    {
        "title": "Scrum & Agile Foundations",
        "category": "Scrum & Agile",
        "duration": "4 weeks",
        "schedule": "Flexible Cohorts",
        "description": (
            "Practical Scaled Agile and Scrum masterclass engineered for aspiring Scrum Masters, Product Owners, "
            "and delivery managers. Deep dive into sprint telemetry, backlog grooming, impediment resolution, "
            "and cross-functional squad leadership with formal verifiable certification."
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
            help="Remove the exact deployment smoke-test enquiry and QA users.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Required with --cleanup; confirms the exact records may be deleted.",
        )
        parser.add_argument(
            "--allow-production-cleanup",
            action="store_true",
            help="Permit --cleanup outside DEBUG. Use only after reviewing the records.",
        )

    def handle(self, *args, **options):
        if options["cleanup"]:
            if not options["confirm"]:
                raise CommandError("--cleanup requires --confirm")
            if not settings.DEBUG and not options["allow_production_cleanup"]:
                raise CommandError(
                    "--cleanup outside DEBUG requires --allow-production-cleanup"
                )
            enquiries = Enquiry.objects.filter(name="Deploy Smoke Test").delete()[0]
            from django.contrib.auth import get_user_model

            qa = (
                get_user_model()
                .objects.filter(
                    email__in=[
                        "qa.smoke@example.com",
                        "qa.apply@example.com",
                        "zq-smoke@example.net",
                    ]
                )
                .delete()[0]
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Removed {enquiries} enquiry row(s), {qa} exact QA user(s)."
                )
            )
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
