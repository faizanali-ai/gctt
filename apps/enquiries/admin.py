from django.contrib import admin

from .models import Enquiry


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "category", "status", "created_at")
    list_filter = ("status", "category")
    search_fields = ("name", "email", "message")
    list_editable = ("status",)
    readonly_fields = ("created_at",)
