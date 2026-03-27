from django.contrib import admin

from analytics.models import Event, TrackingSession, Visitor


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ("client_id", "project", "browser", "device", "country_code", "is_bot", "last_seen")
    list_filter = ("project", "device", "country_code", "is_bot")
    search_fields = ("client_id", "country_name", "bot_name")
    raw_id_fields = ("project",)


@admin.register(TrackingSession)
class TrackingSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "visitor", "started_at", "last_activity_at")
    list_filter = ("project",)
    raw_id_fields = ("project", "visitor")
    date_hierarchy = "started_at"


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "project", "event_type", "event_name", "page_type", "title", "source_group")
    list_filter = ("event_type", "project", "page_type", "source_group")
    search_fields = ("url", "title", "content_title", "event_name", "campaign")
    date_hierarchy = "occurred_at"
    raw_id_fields = ("project", "visitor", "session")
