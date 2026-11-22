CAREER_ARCHETYPES = [
    {
        "keywords": ["ai ba", "ai", "artificial intelligence", "llm", "genai", "prompt", "machine learning", "data"],
        "track": "AI-Powered Business Analyst (AI BA)",
        "programme": "AI BA",
        "fit_score": 96,
        "timeline": "8 Weeks",
        "market_comp": "$115,000 – $145,000 / year ($65 – $85/hr W2)",
        "summary": "AI is redefining enterprise business analysis. Combining traditional requirement elicitation with generative AI tools, prompt engineering, and automated modeling places you at the leading edge of technology transformations.",
        "milestones": [
            "Week 1–2: Enterprise BA Foundations & AI-Augmented Requirement Elicitation",
            "Week 3–4: Prompt Engineering for BRD/FRD Authoring & User Story Generation",
            "Week 5–6: Data Modeling, Predictive Analytics Translation & Workflow Automation",
            "Week 7–8: Capstone AI Enterprise Case Study & Client Placement Preparation",
        ],
    },
    {
        "keywords": ["ba sm", "dual", "hybrid", "product owner", "po", "epic", "squad lead"],
        "track": "Dual Business Analyst & Scrum Master (BA SM)",
        "programme": "BA SM",
        "fit_score": 95,
        "timeline": "8 Weeks",
        "market_comp": "$110,000 – $140,000 / year ($60 – $80/hr W2)",
        "summary": "The dual BA/SM skillset is among the most sought-after profiles in modern agile enterprises. You bridge the gap between executive business requirements and daily agile delivery squads.",
        "milestones": [
            "Week 1–2: Requirements Engineering, Gap Analysis & Enterprise Process Mapping",
            "Week 3–4: Agile User Story Decomposition, Acceptance Criteria & Backlog Refinement",
            "Week 5–6: Scrum Ceremonies, Impediment Removal & Velocity Metrics in Jira",
            "Week 7–8: End-to-End Enterprise Sprint Simulation & Interview Acceleration",
        ],
    },
    {
        "keywords": ["business analyst", "ba", "requirements", "brd", "frd", "bpmn", "stakeholder", "gap analysis", "systems analyst"],
        "track": "Enterprise Business Analyst (Business Analyst)",
        "programme": "Business Analyst",
        "fit_score": 95,
        "timeline": "8 Weeks",
        "market_comp": "$105,000 – $135,000 / year ($55 – $75/hr W2)",
        "summary": "Analytical thinking and stakeholder communication are the core pillars of business analysis. Our curriculum prepares you to lead enterprise elicitation workshops, craft unambiguous specifications, and govern UAT cycles.",
        "milestones": [
            "Week 1–2: Requirements Discovery, Stakeholder Management & Scope Definition",
            "Week 3–4: Process Modeling (BPMN), Use Cases & Technical Specification",
            "Week 5–6: User Acceptance Testing (UAT), Traceability & Change Governance",
            "Week 7–8: Real-World Enterprise SOW Delivery & Executive Mock Interviews",
        ],
    },
    {
        "keywords": ["scrum", "agile", "agile_leadership", "project", "pmp", "coordinator", "lead", "delivery", "master"],
        "track": "Enterprise Agile & Scrum Master (Agile Training)",
        "programme": "Agile Training",
        "fit_score": 94,
        "timeline": "6 Weeks",
        "market_comp": "$110,000 – $135,000 / year ($55 – $75/hr W2)",
        "summary": "Cross-functional communication and servant leadership drive high-velocity engineering teams. Our enterprise curriculum prepares you for Scaled Agile and Scrum leadership with practical sprint delivery simulations.",
        "milestones": [
            "Week 1–2: Scrum Framework, Team Dynamics, Artifacts & Ceremony Facilitation",
            "Week 3–4: Scaled Agile Framework (SAFe), PI Planning & Dependency Resolution",
            "Week 5–6: Jira Enterprise Telemetry, Velocity Analytics & Production Mock Audits",
        ],
    },
    {
        "keywords": ["cloud_engineering", "cloud", "devops", "qa", "test", "docker", "kubernetes", "linux", "ci/cd", "infra", "engineer", "python", "developer"],
        "track": "Enterprise DevOps & Cloud Engineering (DevOps)",
        "programme": "DevOps",
        "fit_score": 93,
        "timeline": "10 Weeks",
        "market_comp": "$125,000 – $160,000 / year ($70 – $95/hr W2)",
        "summary": "High-throughput cloud engineering and resilient deployment pipelines are essential to enterprise modern architectures. Master CI/CD automation, container orchestration, and Infrastructure as Code.",
        "milestones": [
            "Week 1–3: Linux Systems Engineering, Shell Automation & GitOps Workflows",
            "Week 4–6: Docker Containerization & Multi-Cluster Kubernetes Orchestration",
            "Week 7–8: Infrastructure as Code (Terraform) & Cloud Architecture (AWS/GCP)",
            "Week 9–10: Production Observability, Chaos Resilience & Hiring Presentation",
        ],
    },
    {
        "keywords": ["high_paying_erp", "sap", "erp", "financ", "account", "fico", "mm", "procure"],
        "track": "Enterprise ERP & SAP S/4HANA Integration",
        "programme": "SAP S/4HANA Fundamentals",
        "fit_score": 92,
        "timeline": "8 Weeks",
        "market_comp": "$115,000 – $145,000 / year ($65 – $85/hr W2)",
        "summary": "Fortune 500 enterprises rely on modern ERP architectures for core operations. Learn how enterprise processes integrate seamlessly with enterprise accounting and procurement ledgers.",
        "milestones": [
            "Week 1–3: Enterprise Master Data & Business Process Architecture",
            "Week 4–6: Functional Configuration, Ledger Workflows & System Integration",
            "Week 7–8: End-to-End Migration Simulation & Certification Practice",
        ],
    },
    {
        "keywords": ["career_restart", "restart", "career break", "parent", "return", "transition", "non-tech", "admin", "sales", "teacher"],
        "track": "GCTT Career Restart: Accelerated Enterprise Tech Pathway",
        "programme": "Business Analyst",
        "fit_score": 90,
        "timeline": "8 to 10 Weeks",
        "market_comp": "$85,000 – $115,000 / year ($45 – $65/hr W2)",
        "summary": "Our Career Restart pathway is tailored specifically for professionals returning after a career break or transitioning industries. We combine practical enterprise business fundamentals with structured interview preparation.",
        "milestones": [
            "Week 1–3: Enterprise Technology Foundations & Core Communication Mastery",
            "Week 4–6: Business Analysis & Agile Delivery Specialization",
            "Week 7–8: Capstone Portfolio Building & 1-on-1 Executive Placement Coaching",
        ],
    },
]


def analyze_career_trajectory(current_role="", experience_years="", interests=""):
    combined = f"{current_role} {interests} {experience_years}".lower()

    best_match = CAREER_ARCHETYPES[-1]  # Default to Career Restart
    max_matches = 0

    for archetype in CAREER_ARCHETYPES:
        matches = sum(1 for kw in archetype["keywords"] if kw in combined)
        if matches > max_matches:
            max_matches = matches
            best_match = archetype

    return best_match
