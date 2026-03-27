import uuid

from django.conf import settings
from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    tracking_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    domain = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional label for the site being tracked.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name
