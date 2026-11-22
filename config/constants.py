COMPANY = {
    "name": "GCTT",
    "legal_name": "Global Center for Technology & Training",
    "tagline": "Technology talent and training for enterprise teams.",
    "email": "accounts@gctekton.com",
    "jobs_email": "jobs@gctekton.com",
    "jobsEmail": "jobs@gctekton.com",
    "phone": "+1 (786) 855-8859",
    "phone_raw": "+17868558859",
    "address": "2612 Laramie St, Irving TX 75062",
    "domain": "gctekton.com",
    "url": "https://gctekton.com",
}

SERVICES = [
    {
        "url": "/it-staffing/",
        "title": "IT Staffing",
        "text": "Contract, contract-to-hire and direct placement for engineering, cloud and infrastructure teams.",
    },
    {
        "url": "/recruitment/",
        "title": "Recruitment",
        "text": "Retained and contingent search for senior technical practitioners, screened against the role.",
    },
    {
        "url": "/talent-acquisition/",
        "title": "Talent Acquisition",
        "text": "Workforce advisory and embedded recruiting support for teams building delivery capability.",
    },
    {
        "url": "/training/",
        "title": "Training & Development",
        "text": "Instructor-led and online programmes in SAP functional domains and Agile delivery.",
    },
]

DIVISIONS = [
    {
        "label": "Talent Solutions",
        "url": "/services/",
        "prefixes": (
            "/services/",
            "/it-staffing/",
            "/recruitment/",
            "/talent-acquisition/",
            "/sap-scrum/",
            "/employers/",
        ),
        "description": "Staffing, search and SAP delivery talent.",
    },
    {
        "label": "Academy",
        "url": "/training/",
        "prefixes": ("/training/", "/career-restart/"),
        "description": "Programmes, certification and career transition.",
    },
    {
        "label": "Careers",
        "url": "/careers/",
        "prefixes": ("/careers/",),
        "description": "Open mandates across our client teams.",
    },
    {
        "label": "Company",
        "url": "/about/",
        "prefixes": ("/about/", "/privacy/", "/terms/"),
        "description": "Who we are and how we operate.",
    },
    {
        "label": "Contact",
        "url": "/contact/",
        "prefixes": ("/contact/",),
        "description": "Talk to our Irving, Texas team.",
    },
]

NAV_ITEMS = [{"label": item["label"], "url": item["url"]} for item in DIVISIONS]
