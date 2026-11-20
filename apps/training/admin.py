from django.contrib import admin

from .models import Category, Programme, Registration


class RegistrationInline(admin.TabularInline):
    model = Registration
    extra = 0
    readonly_fields = ("student", "created_at")
    fields = ("student", "status", "created_at")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "published", "order")
    list_editable = ("published", "order")


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "delivery_mode", "registration_open", "published", "order")
    list_filter = ("published", "registration_open", "delivery_mode", "category")
    search_fields = ("title", "description")
    list_editable = ("registration_open", "published", "order")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [RegistrationInline]
    # Legacy field: the public design no longer displays programme photography.
    exclude = ("image_url",)


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("student", "programme", "status", "created_at")
    list_filter = ("status", "programme")
    search_fields = ("student__email", "programme__title")
    list_editable = ("status",)
