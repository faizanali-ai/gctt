"""
LinkedIn post copy generator for Academy training programmes.
Generates structured, high-engagement post copy matching GCTT brand marketing standards.
"""

def generate_programme_linkedin_post(programme, request=None):
    base_url = "https://gctekton.com"
    if request:
        base_url = request.build_absolute_uri("/").rstrip("/")
    url = f"{base_url}/training/{programme.slug}/"

    title = programme.title
    duration = programme.duration or "6–8 weeks"
    mode = programme.get_delivery_mode_display()
    schedule = programme.schedule or "Weekend & Evening Cohorts"
    category = programme.category.name if programme.category else "Technology"

    title_lower = title.lower()

    if "ai ba" in title_lower or ("business analyst" in title_lower and "ai" in title_lower):
        hook = "🤖 Accelerate Your Career with AI — Modern AI-Powered Business Analyst (AI BA)!"
        pay = "💼 High-Growth Domain: $115,000 – $140,000 / year"
        learn = [
            "AI/ML Project Scoping & Rapid Requirements Discovery with LLMs",
            "Automated Documentation Generation & Prompt Engineering",
            "Predictive Workflow Modeling & Digital Transformation Governance",
            "Enterprise Business Analysis with Generative AI Tooling",
        ]
        prereq = "💡 Open to analytical thinkers from any background · No prior machine learning coding required!"
        tags = "#GCTT #AIBA #BusinessAnalyst #ArtificialIntelligence #GenAI #TechCareers #PromptEngineering"
    elif "ba sm" in title_lower or ("scrum" in title_lower and "analyst" in title_lower):
        hook = "⚡ Dual Specialization: Bridge Business Analysis & Scrum Master Leadership (BA SM)!"
        pay = "💼 High Demand: $110,000 – $135,000 / year"
        learn = [
            "Requirements Translation into Agile Epics & User Stories",
            "Sprint Backlog Grooming & Agile Ceremony Facilitation",
            "Cross-functional stakeholder alignment, gap analysis & UAT",
            "End-to-End Product Delivery Governance",
        ]
        prereq = "💡 Open to non-technical backgrounds and career transitioners!"
        tags = "#GCTT #BASM #BusinessAnalyst #ScrumMaster #AgileDelivery #TechCareers #HybridDelivery"
    elif "scrum" in title_lower or "agile" in title_lower:
        hook = "🚀 Launch Your Career in Agile — Become a Certified Scrum Master!"
        pay = "💼 U.S. Average Base Pay: $115,875 / year"
        learn = [
            "Deep Understanding of Scrum Framework & Agile Fundamentals",
            "Scrum Master Roles, Responsibilities & Servant Leadership",
            "Sprint Planning, Daily Standups, Reviews & Retrospectives",
            "Impediment resolution & team collaboration in real enterprise projects",
        ]
        prereq = "💡 NO CODING REQUIRED! Open to all majors, recent graduates, and career returners."
        tags = "#GCTT #ScrumMaster #AgileTraining #CareerRestart #TechCareers #Scrum #Upskill"
    elif "business analyst" in title_lower:
        hook = "📊 Enterprise Business Analyst Certification — From Requirements to Delivery!"
        pay = "💼 Indicative Market Benchmark: $95,000 – $120,000 / year"
        learn = [
            "Requirements Elicitation & BRD / FRD Authoring",
            "Process Mapping (BPMN) & Stakeholder Alignment",
            "Gap Analysis, User Acceptance Testing (UAT) & Traceability",
            "Hands-on Enterprise Case Studies",
        ]
        prereq = "💡 Open to graduates and professionals from any domain!"
        tags = "#GCTT #BusinessAnalyst #Requirements #BPMN #Agile #TechCareers #Upskill"
    elif "devops" in title_lower:
        hook = "☁️ Master Cloud & Systems Engineering — Intensive DevOps Certification!"
        pay = "💼 U.S. Average Compensation: $115,000 – $145,000 / year"
        learn = [
            "Modern CI/CD Pipelines & Linux Administration",
            "Docker Containerization & Kubernetes Orchestration",
            "Infrastructure as Code & Cloud Fundamentals",
            "Production Telemetry, Monitoring & Observability",
        ]
        prereq = "💡 Basic IT / operating system familiarity; hands-on labs from Day 1."
        tags = "#GCTT #DevOps #CloudEngineering #Kubernetes #Docker #AWS #Linux #TechCareers"
    else:
        hook = f"🎓 Master {title} with GCTT Academy!"
        pay = "💼 High-Demand Enterprise Skillset"
        learn = [
            f"Comprehensive {category} curriculum led by industry practitioners",
            "Hands-on case studies and real-world delivery simulations",
            "Verifiable completion certificate backed by Texas E-Verify employer",
        ]
        prereq = "💡 Built for working professionals and career transitioners."
        tags = "#GCTT #TechCareers #ITTraining #Upskill #ProfessionalDevelopment"

    bullet_points = "\n".join(f"• {item}" for item in learn)

    text = f"""{hook}

{prereq}
Want to enter the IT industry, transition into a new career, or upgrade your professional skills? GCTT's {title} cohort is built for working professionals.

{pay}
📅 {duration} · {schedule} · {mode}
🎓 Verifiable completion certificate with Texas E-Verify employer backing

✨ What You'll Learn:
{bullet_points}

👉 Register Now & Explore Cohort Details:
{url}

📧 Questions? Email us: trainings@gctekton.com
GCTT — Upskill. Lead. Grow.

{tags}"""
    return text.strip()
