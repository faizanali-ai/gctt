from django.db import migrations


def seed_programmes(apps, schema_editor):
    Category = apps.get_model("training", "Category")
    Programme = apps.get_model("training", "Programme")

    categories_data = [
        {"name": "Agile & Scrum", "order": 1, "published": True},
        {"name": "Business Analysis", "order": 2, "published": True},
        {"name": "Cloud & DevOps", "order": 3, "published": True},
        {"name": "Hybrid Delivery", "order": 4, "published": True},
        {"name": "AI & Emerging Tech", "order": 5, "published": True},
    ]

    categories = {}
    for cat_data in categories_data:
        cat, _ = Category.objects.get_or_create(
            name=cat_data["name"],
            defaults={"order": cat_data["order"], "published": cat_data["published"]},
        )
        if not cat.published or cat.order != cat_data["order"]:
            cat.published = True
            cat.order = cat_data["order"]
            cat.save(update_fields=["published", "order"])
        categories[cat.name] = cat

    programmes_data = [
        {
            "title": "Agile Training",
            "slug": "agile-training",
            "category": "Agile & Scrum",
            "delivery_mode": "online",
            "duration": "6 weeks",
            "schedule": "Weekend & Evening Cohorts",
            "description": (
                "Practical Scaled Agile and Scrum masterclass engineered for aspiring Scrum Masters, "
                "Product Owners, and delivery leads. Deep dive into sprint telemetry, backlog grooming, "
                "impediment resolution, and cross-functional squad leadership with formal verifiable certification."
            ),
            "registration_open": True,
            "published": True,
            "order": 1,
        },
        {
            "title": "Business Analyst",
            "slug": "business-analyst",
            "category": "Business Analysis",
            "delivery_mode": "online",
            "duration": "8 weeks",
            "schedule": "Flexible Evening Cohorts",
            "description": (
                "Comprehensive enterprise business analysis programme covering requirements elicitation, "
                "BRD/FRD authoring, process mapping (BPMN), stakeholder alignment, gap analysis, and "
                "user acceptance testing (UAT) with hands-on enterprise case studies."
            ),
            "registration_open": True,
            "published": True,
            "order": 2,
        },
        {
            "title": "DevOps",
            "slug": "devops",
            "category": "Cloud & DevOps",
            "delivery_mode": "online",
            "duration": "10 weeks",
            "schedule": "Weekend Immersive",
            "description": (
                "Enterprise cloud and systems engineering intensive covering modern CI/CD pipelines, "
                "Docker containerization, Kubernetes orchestration, Linux administration, Infrastructure as Code, "
                "and production observability."
            ),
            "registration_open": True,
            "published": True,
            "order": 3,
        },
        {
            "title": "BA SM",
            "slug": "ba-sm",
            "category": "Hybrid Delivery",
            "delivery_mode": "online",
            "duration": "8 weeks",
            "schedule": "Weekend & Evening Batches",
            "description": (
                "High-impact dual specialization bridging Business Analysis and Scrum Master competencies. "
                "Master requirements translation into agile epics, user story decomposition, sprint backlog grooming, "
                "sprint facilitation, and end-to-end product delivery governance."
            ),
            "registration_open": True,
            "published": True,
            "order": 4,
        },
        {
            "title": "AI BA",
            "slug": "ai-ba",
            "category": "AI & Emerging Tech",
            "delivery_mode": "online",
            "duration": "8 weeks",
            "schedule": "Evening Live Sessions",
            "description": (
                "Modern enterprise business analysis accelerated with artificial intelligence. Learn AI/ML project scoping, "
                "prompt engineering for rapid requirements discovery, automated documentation generation, predictive workflow modeling, "
                "and managing AI-driven digital transformations."
            ),
            "registration_open": True,
            "published": True,
            "order": 5,
        },
    ]

    # Ensure any legacy demo placeholder programmes are unlisted
    Programme.objects.filter(
        slug__in=["scrum-agile-foundations", "sap-mm-fundamentals"]
    ).update(published=False)

    for prog_data in programmes_data:
        cat = categories[prog_data["category"]]
        slug = prog_data["slug"]
        prog = Programme.objects.filter(slug=slug).first()
        if not prog:
            prog = Programme.objects.filter(title=prog_data["title"]).first()

        fields = {
            "title": prog_data["title"],
            "slug": slug,
            "category": cat,
            "delivery_mode": prog_data["delivery_mode"],
            "duration": prog_data["duration"],
            "schedule": prog_data["schedule"],
            "description": prog_data["description"],
            "registration_open": prog_data["registration_open"],
            "published": prog_data["published"],
            "order": prog_data["order"],
        }

        if prog:
            for k, v in fields.items():
                setattr(prog, k, v)
            prog.save()
        else:
            Programme.objects.create(**fields)


def reverse_seed(apps, schema_editor):
    Programme = apps.get_model("training", "Programme")
    Programme.objects.filter(
        slug__in=["agile-training", "business-analyst", "devops", "ba-sm", "ai-ba"]
    ).update(published=False)


class Migration(migrations.Migration):

    dependencies = [
        ("training", "0006_programme_updated_at"),
    ]

    operations = [
        migrations.RunPython(seed_programmes, reverse_seed),
    ]
