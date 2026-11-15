from django.contrib import admin

from .models import Enquiry


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "category", "company", "status", "created_at")
    list_filter = ("status", "category", "how_heard")
    search_fields = ("name", "email", "company", "message")
    list_editable = ("status",)
    readonly_fields = ("created_at",)
