from django.db import models


class Visitor(models.Model):
    project = models.ForeignKey(
        "core.Project",
        on_delete=models.CASCADE,
        related_name="visitors",
    )
    client_id = models.CharField(max_length=64)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    browser = models.CharField(max_length=128, blank=True)
    os = models.CharField(max_length=128, blank=True)
    device = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    country_code = models.CharField(max_length=8, blank=True)
    country_name = models.CharField(max_length=128, blank=True)
    is_bot = models.BooleanField(default=False)
    bot_name = models.CharField(max_length=128, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "client_id"],
                name="unique_visitor_per_project",
            ),
        ]
        indexes = [
            models.Index(fields=["project", "client_id"]),
            models.Index(fields=["project", "country_code"]),
            models.Index(fields=["project", "is_bot"]),
        ]

    def __str__(self) -> str:
        return f"{self.client_id} ({self.project_id})"


class TrackingSession(models.Model):
    project = models.ForeignKey(
        "core.Project",
        on_delete=models.CASCADE,
        related_name="tracking_sessions",
    )
    visitor = models.ForeignKey(
        Visitor,
        on_delete=models.CASCADE,
        related_name="tracking_sessions",
    )
    client_session_id = models.CharField(max_length=64, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField()
    landing_url = models.TextField(blank=True)
    landing_title = models.CharField(max_length=512, blank=True)
    landing_page_type = models.CharField(max_length=64, blank=True)
    landing_category = models.CharField(max_length=255, blank=True)
    source_group = models.CharField(max_length=64, blank=True)
    source_name = models.CharField(max_length=255, blank=True)
    medium = models.CharField(max_length=255, blank=True)
    campaign = models.CharField(max_length=255, blank=True)
    referrer_domain = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["project", "visitor", "-last_activity_at"]),
            models.Index(fields=["project", "started_at", "source_group"]),
        ]


class Event(models.Model):
    class EventType(models.TextChoices):
        PAGEVIEW = "pageview", "Pageview"
        CLICK = "click", "Click"
        PAGE_EXIT = "page_exit", "Page Exit"
        SCROLL_DEPTH = "scroll_depth", "Scroll Depth"
        ENGAGED_VISIT = "engaged_visit", "Engaged Visit"
        CTA_CLICK = "cta_click", "CTA Click"
        CUSTOM = "custom", "Custom"

    project = models.ForeignKey(
        "core.Project",
        on_delete=models.CASCADE,
        related_name="events",
    )
    visitor = models.ForeignKey(
        Visitor,
        on_delete=models.CASCADE,
        related_name="events",
    )
    session = models.ForeignKey(
        TrackingSession,
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    url = models.TextField()
    title = models.CharField(max_length=512, blank=True)
    referrer = models.TextField(blank=True)
    occurred_at = models.DateTimeField()
    screen_width = models.PositiveIntegerField(null=True, blank=True)
    screen_height = models.PositiveIntegerField(null=True, blank=True)
    language = models.CharField(max_length=32, blank=True)
    event_name = models.CharField(max_length=128, blank=True)
    page_type = models.CharField(max_length=64, blank=True)
    content_id = models.CharField(max_length=128, blank=True)
    content_slug = models.CharField(max_length=255, blank=True)
    content_title = models.CharField(max_length=512, blank=True)
    author = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=255, blank=True)
    tags = models.JSONField(default=list, blank=True)
    utm_source = models.CharField(max_length=255, blank=True)
    utm_medium = models.CharField(max_length=255, blank=True)
    utm_campaign = models.CharField(max_length=255, blank=True)
    utm_content = models.CharField(max_length=255, blank=True)
    utm_term = models.CharField(max_length=255, blank=True)
    source_group = models.CharField(max_length=64, blank=True)
    source_name = models.CharField(max_length=255, blank=True)
    medium = models.CharField(max_length=255, blank=True)
    campaign = models.CharField(max_length=255, blank=True)
    destination_url = models.TextField(blank=True)
    cta_name = models.CharField(max_length=255, blank=True)
    scroll_percent = models.PositiveSmallIntegerField(null=True, blank=True)
    engaged_seconds = models.PositiveIntegerField(null=True, blank=True)
    properties = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["project", "occurred_at"]),
            models.Index(fields=["session", "event_type"]),
            models.Index(fields=["project", "event_name"]),
            models.Index(fields=["project", "page_type"]),
            models.Index(fields=["project", "source_group"]),
        ]
