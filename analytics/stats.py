from __future__ import annotations

from datetime import datetime, timedelta

from django.db.models import Avg, Case, Count, F, Max, Q, Value, When
from django.db.models.fields import TextField
from django.db.models.functions import TruncDate
from django.utils import timezone

from analytics.models import Event, TrackingSession
from core.models import Project


FILTER_ALL = "__all__"


def normalize_filter_value(value: str) -> str:
    value = (value or "").strip()
    return value or FILTER_ALL


def apply_event_filters(queryset, filters: dict):
    if not filters["include_bots"]:
        queryset = queryset.filter(visitor__is_bot=False)
    if filters["source"] != FILTER_ALL:
        queryset = queryset.filter(source_group=filters["source"])
    if filters["page_type"] != FILTER_ALL:
        queryset = queryset.filter(page_type=filters["page_type"])
    if filters["category"] != FILTER_ALL:
        queryset = queryset.filter(category=filters["category"])
    if filters["device"] != FILTER_ALL:
        queryset = queryset.filter(visitor__device=filters["device"])
    return queryset


def apply_session_filters(queryset, filters: dict):
    if not filters["include_bots"]:
        queryset = queryset.filter(visitor__is_bot=False)
    if filters["source"] != FILTER_ALL:
        queryset = queryset.filter(source_group=filters["source"])
    if filters["page_type"] != FILTER_ALL:
        queryset = queryset.filter(landing_page_type=filters["page_type"])
    if filters["category"] != FILTER_ALL:
        queryset = queryset.filter(landing_category=filters["category"])
    if filters["device"] != FILTER_ALL:
        queryset = queryset.filter(visitor__device=filters["device"])
    return queryset


def available_filters(project: Project, start: datetime, end: datetime) -> dict:
    ev_qs = Event.objects.filter(project=project, occurred_at__gte=start, occurred_at__lt=end)
    return {
        "sources": [
            row["source_group"]
            for row in ev_qs.exclude(source_group="").values("source_group").distinct().order_by("source_group")
        ],
        "page_types": [
            row["page_type"]
            for row in ev_qs.exclude(page_type="").values("page_type").distinct().order_by("page_type")
        ],
        "categories": [
            row["category"]
            for row in ev_qs.exclude(category="").values("category").distinct().order_by("category")
        ],
        "devices": [
            row["visitor__device"]
            for row in ev_qs.exclude(visitor__device="").values("visitor__device").distinct().order_by("visitor__device")
        ],
    }


def project_stats(
    project: Project,
    start: datetime,
    end: datetime,
    filters: dict | None = None,
) -> dict:
    filters = filters or {
        "source": FILTER_ALL,
        "page_type": FILTER_ALL,
        "category": FILTER_ALL,
        "device": FILTER_ALL,
        "include_bots": False,
    }
    ev_qs = apply_event_filters(
        Event.objects.filter(project=project, occurred_at__gte=start, occurred_at__lt=end),
        filters,
    )
    pageview_qs = ev_qs.filter(event_type=Event.EventType.PAGEVIEW)
    sessions_qs = apply_session_filters(
        TrackingSession.objects.filter(project=project, started_at__gte=start, started_at__lt=end),
        filters,
    ).annotate(
        pv_count=Count("events", filter=Q(events__event_type=Event.EventType.PAGEVIEW)),
    )

    pageviews = pageview_qs.count()
    unique_visitors = ev_qs.values("visitor_id").distinct().count()
    total_sessions = sessions_qs.count()
    bounced = sessions_qs.filter(pv_count=1).count()
    bounce_rate = (bounced / total_sessions * 100.0) if total_sessions else 0.0
    returning_visitors = (
        pageview_qs.values("visitor_id")
        .annotate(session_count=Count("session_id", distinct=True))
        .filter(session_count__gt=1)
        .count()
    )
    bot_views = Event.objects.filter(
        project=project,
        occurred_at__gte=start,
        occurred_at__lt=end,
        event_type=Event.EventType.PAGEVIEW,
        visitor__is_bot=True,
    ).count()
    avg_engaged_seconds = (
        ev_qs.filter(event_type=Event.EventType.ENGAGED_VISIT)
        .aggregate(avg=Avg("engaged_seconds"))
        .get("avg")
        or 0
    )

    traffic_by_day = list(
        pageview_qs.annotate(day=TruncDate("occurred_at"))
        .values("day")
        .annotate(views=Count("id"))
        .order_by("day")
    )
    realtime_views_30m = Event.objects.filter(
        project=project,
        event_type=Event.EventType.PAGEVIEW,
        occurred_at__gte=timezone.now() - timedelta(minutes=30),
        visitor__is_bot=False,
    ).count()
    realtime_active_visitors_30m = (
        Event.objects.filter(
            project=project,
            occurred_at__gte=timezone.now() - timedelta(minutes=30),
            visitor__is_bot=False,
        )
        .values("visitor_id")
        .distinct()
        .count()
    )

    device_breakdown = list(
        pageview_qs.values("visitor__device").annotate(count=Count("id")).order_by("-count")
    )
    os_breakdown = list(
        pageview_qs.values("visitor__os").annotate(count=Count("id")).order_by("-count")[:12]
    )
    browser_breakdown = list(
        pageview_qs.values("visitor__browser").annotate(count=Count("id")).order_by("-count")[:12]
    )
    country_breakdown = list(
        pageview_qs.values("visitor__country_name").annotate(count=Count("id")).order_by("-count")[:12]
    )
    top_referrers = list(
        pageview_qs.annotate(
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
        pageview_qs.values("url").annotate(views=Count("id")).order_by("-views")[:10]
    )
    landing_pages = list(
        sessions_qs.values("landing_url").annotate(sessions=Count("id")).order_by("-sessions")[:10]
    )
    traffic_by_source = list(
        pageview_qs.values("source_group", "source_name", "medium")
        .annotate(views=Count("id"), visitors=Count("visitor_id", distinct=True))
        .order_by("-views")[:10]
    )
    top_campaigns = list(
        pageview_qs.exclude(campaign="")
        .values("campaign")
        .annotate(views=Count("id"), visitors=Count("visitor_id", distinct=True))
        .order_by("-views")[:10]
    )
    top_content = list(
        pageview_qs.exclude(content_title="")
        .values("content_title", "content_slug", "category")
        .annotate(
            views=Count("id"),
            unique_visitors=Count("visitor_id", distinct=True),
        )
        .order_by("-views")[:10]
    )
    scroll_completion = list(
        ev_qs.filter(event_type=Event.EventType.SCROLL_DEPTH)
        .values("url")
        .annotate(max_scroll=Max("scroll_percent"))
        .order_by("-max_scroll")[:10]
    )
    exit_pages = list(
        ev_qs.filter(event_type=Event.EventType.PAGE_EXIT)
        .values("url")
        .annotate(exits=Count("id"))
        .order_by("-exits")[:10]
    )
    internal_clicks = list(
        ev_qs.filter(event_type=Event.EventType.CTA_CLICK)
        .exclude(destination_url="")
        .values("destination_url")
        .annotate(clicks=Count("id"))
        .order_by("-clicks")[:10]
    )
    conversion_report = list(
        ev_qs.filter(
            Q(event_type=Event.EventType.CUSTOM)
            | Q(event_name__in=["signup", "login", "post_create", "comment_create", "like", "share", "follow"])
        )
        .values("event_name", "source_group", "content_title", "url")
        .annotate(conversions=Count("id"))
        .order_by("-conversions")[:20]
    )

    return {
        "pageviews": pageviews,
        "unique_visitors": unique_visitors,
        "total_sessions": total_sessions,
        "returning_visitors": returning_visitors,
        "bounce_rate": round(bounce_rate, 1),
        "avg_engaged_seconds": round(avg_engaged_seconds, 1) if avg_engaged_seconds else 0,
        "bot_views": bot_views,
        "traffic_by_day": traffic_by_day,
        "device_breakdown": device_breakdown,
        "os_breakdown": os_breakdown,
        "browser_breakdown": browser_breakdown,
        "country_breakdown": country_breakdown,
        "top_referrers": top_referrers,
        "top_pages": top_pages,
        "landing_pages": landing_pages,
        "traffic_by_source": traffic_by_source,
        "top_campaigns": top_campaigns,
        "top_content": top_content,
        "scroll_completion": scroll_completion,
        "exit_pages": exit_pages,
        "internal_clicks": internal_clicks,
        "conversion_report": conversion_report,
        "realtime_views_30m": realtime_views_30m,
        "realtime_active_visitors_30m": realtime_active_visitors_30m,
        "available_filters": available_filters(project, start, end),
    }


def period_bounds(period: str, now=None):
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


def kpi_comparison(project: Project, period: str, filters: dict | None = None) -> dict:
    start, end = period_bounds(period)
    pstart, pend = previous_period_bounds(period)
    c = project_stats(project, start, end, filters=filters)
    p = project_stats(project, pstart, pend, filters=filters)
    return {
        "pageviews_delta_pct": _pct_delta(c["pageviews"], p["pageviews"]),
        "unique_visitors_delta_pct": _pct_delta(c["unique_visitors"], p["unique_visitors"]),
        "total_sessions_delta_pct": _pct_delta(c["total_sessions"], p["total_sessions"]),
        "bounce_delta_pts": round(c["bounce_rate"] - p["bounce_rate"], 1),
        "returning_visitors_delta_pct": _pct_delta(c["returning_visitors"], p["returning_visitors"]),
        "avg_engaged_seconds_delta_pct": _pct_delta(c["avg_engaged_seconds"], p["avg_engaged_seconds"]),
    }
