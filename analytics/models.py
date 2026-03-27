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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "client_id"],
                name="unique_visitor_per_project",
            ),
        ]
        indexes = [
            models.Index(fields=["project", "client_id"]),
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

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["project", "visitor", "-last_activity_at"]),
        ]


class Event(models.Model):
    class EventType(models.TextChoices):
        PAGEVIEW = "pageview", "Pageview"
        CLICK = "click", "Click"

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

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["project", "occurred_at"]),
            models.Index(fields=["session", "event_type"]),
        ]
