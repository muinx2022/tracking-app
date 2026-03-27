from __future__ import annotations

from datetime import datetime, timedelta

from django.db.models import Case, Count, F, Q, Value, When
from django.db.models.fields import TextField
from django.db.models.functions import TruncDate
from django.utils import timezone

from analytics.models import Event, TrackingSession
from core.models import Project


def project_stats(
    project: Project,
    start: datetime,
    end: datetime,
) -> dict:
    """Aggregate metrics for [start, end) in project timezone-aware datetimes."""
    ev_qs = Event.objects.filter(
        project=project,
        occurred_at__gte=start,
        occurred_at__lt=end,
    )
    pageviews = ev_qs.filter(event_type=Event.EventType.PAGEVIEW).count()
    unique_visitors = (
        ev_qs.values("visitor_id").distinct().count()
    )

    sessions_qs = TrackingSession.objects.filter(
        project=project,
        started_at__gte=start,
        started_at__lt=end,
    ).annotate(
        pv_count=Count(
            "events",
            filter=Q(events__event_type=Event.EventType.PAGEVIEW),
        )
    )
    total_sessions = sessions_qs.count()
    bounced = sessions_qs.filter(pv_count=1).count()
    bounce_rate = (bounced / total_sessions * 100.0) if total_sessions else 0.0

    traffic_by_day = list(
        ev_qs.filter(event_type=Event.EventType.PAGEVIEW)
        .annotate(day=TruncDate("occurred_at"))
        .values("day")
        .annotate(views=Count("id"))
        .order_by("day")
    )

    device_breakdown = list(
        ev_qs.filter(event_type=Event.EventType.PAGEVIEW)
        .values("visitor__device")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    os_breakdown = list(
        ev_qs.filter(event_type=Event.EventType.PAGEVIEW)
        .values("visitor__os")
        .annotate(count=Count("id"))
        .order_by("-count")[:12]
    )

    browser_breakdown = list(
        ev_qs.filter(event_type=Event.EventType.PAGEVIEW)
        .values("visitor__browser")
        .annotate(count=Count("id"))
        .order_by("-count")[:12]
    )

    top_referrers = list(
        ev_qs.filter(event_type=Event.EventType.PAGEVIEW)
        .annotate(
            ref_key=Case(
                When(Q(referrer__isnull=True) | Q(referrer=""), then=Value("Direct")),
                default=F("referrer"),
                output_field=TextField(),
            )
        )
        .values("ref_key")
        .annotate(views=Count("id"))
        .order_by("-views")[:10]
    )

    top_pages = list(
        ev_qs.filter(event_type=Event.EventType.PAGEVIEW)
        .values("url")
        .annotate(views=Count("id"))
        .order_by("-views")[:10]
    )

    return {
        "pageviews": pageviews,
        "unique_visitors": unique_visitors,
        "total_sessions": total_sessions,
        "bounce_rate": round(bounce_rate, 1),
        "traffic_by_day": traffic_by_day,
        "device_breakdown": device_breakdown,
        "os_breakdown": os_breakdown,
        "browser_breakdown": browser_breakdown,
        "top_referrers": top_referrers,
        "top_pages": top_pages,
    }


def period_bounds(period: str, now=None):
    """Return (start, end) as timezone-aware datetimes; end is exclusive 'now' for rolling windows."""
    now = now or timezone.now()
    if period == "7d":
        start = now - timedelta(days=7)
    elif period == "30d":
        start = now - timedelta(days=30)
    elif period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now - timedelta(days=7)
    return start, now


def previous_period_bounds(period: str, now=None):
    """Return (prev_start, prev_end) immediately before the current period window."""
    now = now or timezone.now()
    start, end = period_bounds(period, now)
    if period == "today":
        prev_end = start
        prev_start = start - timedelta(days=1)
        return prev_start, prev_end
    length = end - start
    prev_end = start
    prev_start = start - length
    return prev_start, prev_end


def _pct_delta(curr: float, prev: float) -> float | None:
    if prev == 0:
        return None if curr == 0 else 100.0
    return round((curr - prev) / prev * 100.0, 1)


def kpi_comparison(project: Project, period: str) -> dict:
    """Percent / point deltas vs the previous period of equal length (or prior calendar day for today)."""
    start, end = period_bounds(period)
    pstart, pend = previous_period_bounds(period)
    c = project_stats(project, start, end)
    p = project_stats(project, pstart, pend)
    return {
        "pageviews_delta_pct": _pct_delta(c["pageviews"], p["pageviews"]),
        "unique_visitors_delta_pct": _pct_delta(c["unique_visitors"], p["unique_visitors"]),
        "total_sessions_delta_pct": _pct_delta(c["total_sessions"], p["total_sessions"]),
        "bounce_delta_pts": round(c["bounce_rate"] - p["bounce_rate"], 1),
    }
