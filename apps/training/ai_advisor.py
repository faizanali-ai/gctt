CAREER_ARCHETYPES = [
    {
        "keywords": ["financ", "account", "cpa", "audit", "banking", "invoic", "ledger", "bookkeep", "fico", "erp"],
        "track": "SAP S/4HANA Financial Accounting (FI/CO) Consultant",
        "programme": "SAP S/4HANA Financial Accounting Certification",
        "fit_score": 96,
        "timeline": "8 to 10 Weeks",
        "market_comp": "$115,000 – $145,000 / year ($65 – $85/hr W2)",
        "summary": "Your financial background gives you an immense analytical advantage in enterprise ERP. Fortune 500 enterprises are aggressively migrating to SAP S/4HANA and pay top compensation for consultants who understand real accounting rules alongside system ledger configurations.",
        "milestones": [
            "Week 1–3: SAP General Ledger, Accounts Payable/Receivable & Asset Accounting",
            "Week 4–6: Controlling (CO-CCA, CO-PCA, Internal Orders) & S/4HANA Universal Journal",
            "Week 7–8: End-to-End Enterprise Migration Simulation & Practice Cert Exam",
            "Week 9+: Direct GCTT Placement Interviews with Dallas-Fort Worth & Nationwide Mandates"
        ]
    },
    {
        "keywords": ["logistic", "supply", "procure", "inventor", "warehouse", "materi", "manufactur", "sourcing", "mm", "sd"],
        "track": "SAP S/4HANA Sourcing, Procurement & Materials Management (MM/SD)",
        "programme": "SAP S/4HANA Sourcing & Procurement Certification",
        "fit_score": 94,
        "timeline": "8 to 10 Weeks",
        "market_comp": "$110,000 – $140,000 / year ($60 – $80/hr W2)",
        "summary": "Supply chain and procurement professionals are prime candidates for SAP MM/SD specialization. You already grasp inventory flows and vendor procurement—learning S/4HANA procurement configuration bridges your domain knowledge directly into high-paying enterprise contracts.",
        "milestones": [
            "Week 1–3: Enterprise Structure, Material Master & Purchasing Configuration",
            "Week 4–6: Inventory Management, Physical Inventory & Automatic Account Determination",
            "Week 7–8: Integration with Sales (SD) & Finance (FI) + Real-world SOW Scenario",
            "Week 9+: Placement Marketing via GCTT Client Network"
        ]
    },
    {
        "keywords": ["scrum", "agile", "project", "pmp", "coordinator", "business analyst", "operations", "lead"],
        "track": "Enterprise Agile Scrum Master & Delivery Lead",
        "programme": "Professional Scrum Master (PSM I) & Scaled Agile Delivery",
        "fit_score": 95,
        "timeline": "6 to 8 Weeks",
        "market_comp": "$110,000 – $135,000 / year ($55 – $75/hr W2)",
        "summary": "Cross-functional communication and stakeholder management are the most critical skills for modern Agile delivery leads. Our enterprise curriculum prepares you for SAFe and Scrum.org certifications with practical sprint delivery simulations.",
        "milestones": [
            "Week 1–2: Scrum Framework, Artifacts, Events & Team Dynamics",
            "Week 3–4: Scaled Agile Framework (SAFe), PI Planning & Cross-Team Dependencies",
            "Week 5–6: Jira Enterprise Configuration, Velocity Metrics & Mock Audits",
            "Week 7+: Dedicated Recruiter Placement for Direct W2 Corporate Roles"
        ]
    },
    {
        "keywords": ["qa", "test", "quality", "support", "developer", "engineer", "python", "java", "sql", "code", "cloud", "devops"],
        "track": "Enterprise Cloud Architecture & DevOps Integration Lead",
        "programme": "Enterprise Cloud Engineering & SAP Integration",
        "fit_score": 92,
        "timeline": "10 to 12 Weeks",
        "market_comp": "$125,000 – $160,000 / year ($70 – $95/hr W2)",
        "summary": "Having technical or analytical foundational skills positions you perfectly to step into enterprise systems integration. GCTT connects technical specialists with high-value SOW engineering teams.",
        "milestones": [
            "Week 1–4: Modern Cloud Infrastructure, Linux & CI/CD Pipelines",
            "Week 5–8: API Integrations, SAP BTP / Cloud Connectors & Microservices",
            "Week 9–10: High Availability & Disaster Recovery Enterprise Scenarios",
            "Week 11+: Candidate Presentation to Hiring Fortune 500 Clients"
        ]
    },
    {
        "keywords": ["restart", "career break", "parent", "return", "transition", "non-tech", "admin", "sales", "teacher"],
        "track": "GCTT Career Restart: Accelerated Enterprise Tech Pathway",
        "programme": "Career Restart: Functional Systems & Agile Certification",
        "fit_score": 90,
        "timeline": "10 to 12 Weeks",
        "market_comp": "$85,000 – $115,000 / year ($45 – $65/hr W2)",
        "summary": "Our Career Restart programme is tailored specifically for professionals returning after a career break or switching industries. We combine zero-fluff foundational tech training with direct enterprise resume rebuilding and guaranteed placement interviews.",
        "milestones": [
            "Week 1–3: Enterprise Technology Foundations & Professional Confidence Rebuild",
            "Week 4–7: Functional ERP / Agile Specialization & Guided Project Capstone",
            "Week 8–9: Industry Certification Preparation (Scrum / SAP Associate)",
            "Week 10+: 1-on-1 Executive Interview Coaching & GCTT Corporate Representation"
        ]
    }
]


def analyze_career_trajectory(current_role="", experience_years="", interests=""):
    combined = f"{current_role} {interests} {experience_years}".lower()

    # Score each archetype based on keyword matches
    best_match = CAREER_ARCHETYPES[-1]  # Default to Career Restart
    max_matches = 0

    for archetype in CAREER_ARCHETYPES:
        matches = sum(1 for kw in archetype["keywords"] if kw in combined)
        if matches > max_matches:
            max_matches = matches
            best_match = archetype

    return best_match
