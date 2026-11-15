from django.contrib import admin

from .models import Application, Job


class ApplicationInline(admin.TabularInline):
    model = Application
    extra = 0
    readonly_fields = ("applicant", "resume", "created_at")
    fields = ("applicant", "status", "resume", "created_at")


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "location", "employment_type", "published", "created_at")
    list_filter = ("published", "employment_type")
    search_fields = ("title", "description", "location")
    list_editable = ("published",)
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ApplicationInline]


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("applicant", "job", "status", "created_at")
    list_filter = ("status", "job")
    search_fields = ("applicant__email", "job__title")
    list_editable = ("status",)
    actions = ["mark_shortlisted", "mark_rejected"]

    @admin.action(description="Mark selected applications as Shortlisted")
    def mark_shortlisted(self, request, queryset):
        queryset.update(status=Application.Status.SHORTLISTED)

    @admin.action(description="Mark selected applications as Rejected")
    def mark_rejected(self, request, queryset):
        queryset.update(status=Application.Status.REJECTED)
