from django.contrib.sitemaps import Sitemap
from django.db.models import Q

from apps.jobs.models import Job
from apps.training.models import Programme

STATIC_PATHS = [
    "/", "/about/", "/services/", "/it-staffing/", "/recruitment/",
    "/talent-acquisition/", "/sap-scrum/", "/career-restart/", "/employers/",
    "/contact/", "/privacy/", "/terms/", "/careers/", "/training/",
]


class StaticSitemap(Sitemap):
    priority = 0.8
    changefreq = "monthly"

    def items(self):
        return STATIC_PATHS

    def location(self, item):
        return item


class JobSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Job.objects.filter(published=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f"/careers/{obj.slug}/"


class ProgrammeSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Programme.objects.filter(published=True).filter(
            Q(category__isnull=True) | Q(category__published=True)
        )

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f"/training/{obj.slug}/"
