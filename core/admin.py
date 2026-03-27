from django.contrib import admin

from core.models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "tracking_id", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "tracking_id", "domain")
    readonly_fields = ("tracking_id", "created_at")
    raw_id_fields = ("owner",)
