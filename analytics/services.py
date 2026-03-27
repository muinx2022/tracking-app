from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from user_agents import parse as parse_user_agent

from analytics.models import Event, TrackingSession, Visitor
from core.models import Project


SESSION_IDLE = timedelta(minutes=30)


def get_client_ip(request) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    addr = request.META.get("REMOTE_ADDR")
    return addr or None


def parse_ua(user_agent_string: str) -> tuple[str, str, str]:
    ua = parse_user_agent(user_agent_string or "")
    browser = f"{ua.browser.family} {ua.browser.version_string}".strip()
    os_name = f"{ua.os.family} {ua.os.version_string}".strip()
    if ua.is_mobile:
        device = "mobile"
    elif ua.is_tablet:
        device = "tablet"
    elif ua.is_pc:
        device = "desktop"
    else:
        device = "other"
    return browser or "Unknown", os_name or "Unknown", device


def upsert_visitor(
    project: Project,
    client_id: str,
    browser: str,
    os_name: str,
    device: str,
    ip_address: str | None,
) -> Visitor:
    visitor, created = Visitor.objects.get_or_create(
        project=project,
        client_id=client_id,
        defaults={
            "browser": browser,
            "os": os_name,
            "device": device,
            "ip_address": ip_address,
        },
    )
    if not created:
        visitor.browser = browser
        visitor.os = os_name
        visitor.device = device
        visitor.ip_address = ip_address
        visitor.save(update_fields=["browser", "os", "device", "ip_address", "last_seen"])
    return visitor


def resolve_session(
    project: Project,
    visitor: Visitor,
    client_session_id: str = "",
) -> TrackingSession:
    now = timezone.now()
    cutoff = now - SESSION_IDLE
    latest = (
        TrackingSession.objects.filter(project=project, visitor=visitor)
        .order_by("-last_activity_at")
        .first()
    )
    if latest and latest.last_activity_at >= cutoff:
        latest.last_activity_at = now
        latest.save(update_fields=["last_activity_at"])
        return latest
    return TrackingSession.objects.create(
        project=project,
        visitor=visitor,
        client_session_id=client_session_id or "",
        last_activity_at=now,
    )


def record_event(
    project: Project,
    visitor: Visitor,
    session: TrackingSession,
    *,
    event_type: str,
    url: str,
    title: str,
    referrer: str,
    occurred_at,
    screen_width: int | None,
    screen_height: int | None,
    language: str,
) -> Event:
    return Event.objects.create(
        project=project,
        visitor=visitor,
        session=session,
        event_type=event_type,
        url=url,
        title=title,
        referrer=referrer,
        occurred_at=occurred_at,
        screen_width=screen_width,
        screen_height=screen_height,
        language=language,
    )
