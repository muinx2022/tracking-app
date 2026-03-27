from django.contrib import admin

from analytics.models import Event, TrackingSession, Visitor


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ("client_id", "project", "browser", "device", "last_seen")
    list_filter = ("project", "device")
    search_fields = ("client_id",)
    raw_id_fields = ("project",)


@admin.register(TrackingSession)
class TrackingSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "visitor", "started_at", "last_activity_at")
    list_filter = ("project",)
    raw_id_fields = ("project", "visitor")
    date_hierarchy = "started_at"


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "project", "event_type", "title", "url")
    list_filter = ("event_type", "project")
    search_fields = ("url", "title")
    date_hierarchy = "occurred_at"
    raw_id_fields = ("project", "visitor", "session")
