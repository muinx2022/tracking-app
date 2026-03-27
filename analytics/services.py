from __future__ import annotations

from urllib.parse import urlparse

from datetime import timedelta

from django.utils import timezone
from user_agents import parse as parse_user_agent

from analytics.models import Event, TrackingSession, Visitor
from core.models import Project


SESSION_IDLE = timedelta(minutes=30)

SOCIAL_HOSTS = (
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "t.co",
    "twitter.com",
    "x.com",
    "youtube.com",
    "zalo.me",
    "threads.net",
    "reddit.com",
    "tiktok.com",
)

SEARCH_HOSTS = (
    "google.",
    "bing.com",
    "yahoo.com",
    "duckduckgo.com",
    "coccoc.com",
    "baidu.com",
)

COUNTRY_NAMES = {
    "VN": "Vietnam",
    "US": "United States",
    "SG": "Singapore",
    "JP": "Japan",
    "KR": "South Korea",
    "GB": "United Kingdom",
    "DE": "Germany",
    "FR": "France",
    "AU": "Australia",
    "CA": "Canada",
}


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


def detect_bot(user_agent_string: str) -> tuple[bool, str]:
    ua = (user_agent_string or "").lower()
    markers = (
        "bot",
        "crawler",
        "spider",
        "headless",
        "uptime",
        "monitor",
        "lighthouse",
        "pagespeed",
        "curl/",
        "wget/",
        "python-requests",
        "go-http-client",
    )
    if not ua:
        return False, ""
    for marker in markers:
        if marker in ua:
            return True, marker
    return False, ""


def get_country(request) -> tuple[str, str]:
    code = (request.META.get("HTTP_CF_IPCOUNTRY") or "").strip().upper()
    if not code or code in {"XX", "T1"}:
        return "", ""
    return code, COUNTRY_NAMES.get(code, code)


def extract_domain(url: str) -> str:
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return ""
    return host.lower()


def classify_source(referrer: str, utm_source: str, utm_medium: str) -> tuple[str, str, str]:
    source_name = (utm_source or "").strip()
    medium = (utm_medium or "").strip()
    if source_name or medium:
        source_group = "Campaign"
        medium_l = medium.lower()
        source_l = source_name.lower()
        if "social" in medium_l or any(h in source_l for h in ("facebook", "instagram", "linkedin", "tiktok", "zalo")):
            source_group = "Social"
        elif any(k in medium_l for k in ("cpc", "paid", "ppc", "display")):
            source_group = "Paid"
        elif "email" in medium_l:
            source_group = "Email"
        return source_group, source_name or "utm", medium

    domain = extract_domain(referrer)
    if not domain:
        return "Direct", "Direct", ""
    if any(host in domain for host in SOCIAL_HOSTS):
        return "Social", domain, "referral"
    if any(host in domain for host in SEARCH_HOSTS):
        return "Organic Search", domain, "organic"
    return "Referral", domain, "referral"


def upsert_visitor(
    project: Project,
    client_id: str,
    browser: str,
    os_name: str,
    device: str,
    ip_address: str | None,
    country_code: str,
    country_name: str,
    is_bot: bool,
    bot_name: str,
) -> Visitor:
    visitor, created = Visitor.objects.get_or_create(
        project=project,
        client_id=client_id,
        defaults={
            "browser": browser,
            "os": os_name,
            "device": device,
            "ip_address": ip_address,
            "country_code": country_code,
            "country_name": country_name,
            "is_bot": is_bot,
            "bot_name": bot_name,
        },
    )
    if not created:
        visitor.browser = browser
        visitor.os = os_name
        visitor.device = device
        visitor.ip_address = ip_address
        visitor.country_code = country_code
        visitor.country_name = country_name
        visitor.is_bot = is_bot
        visitor.bot_name = bot_name
        visitor.save(
            update_fields=[
                "browser",
                "os",
                "device",
                "ip_address",
                "country_code",
                "country_name",
                "is_bot",
                "bot_name",
                "last_seen",
            ]
        )
    return visitor


def resolve_session(
    project: Project,
    visitor: Visitor,
    client_session_id: str = "",
    *,
    landing_url: str = "",
    landing_title: str = "",
    landing_page_type: str = "",
    landing_category: str = "",
    source_group: str = "",
    source_name: str = "",
    medium: str = "",
    campaign: str = "",
    referrer_domain: str = "",
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
        landing_url=landing_url,
        landing_title=landing_title,
        landing_page_type=landing_page_type,
        landing_category=landing_category,
        source_group=source_group,
        source_name=source_name,
        medium=medium,
        campaign=campaign,
        referrer_domain=referrer_domain,
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
    event_name: str = "",
    page_type: str = "",
    content_id: str = "",
    content_slug: str = "",
    content_title: str = "",
    author: str = "",
    category: str = "",
    tags=None,
    utm_source: str = "",
    utm_medium: str = "",
    utm_campaign: str = "",
    utm_content: str = "",
    utm_term: str = "",
    source_group: str = "",
    source_name: str = "",
    medium: str = "",
    campaign: str = "",
    destination_url: str = "",
    cta_name: str = "",
    scroll_percent: int | None = None,
    engaged_seconds: int | None = None,
    properties=None,
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
        event_name=event_name,
        page_type=page_type,
        content_id=content_id,
        content_slug=content_slug,
        content_title=content_title,
        author=author,
        category=category,
        tags=tags or [],
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        utm_content=utm_content,
        utm_term=utm_term,
        source_group=source_group,
        source_name=source_name,
        medium=medium,
        campaign=campaign,
        destination_url=destination_url,
        cta_name=cta_name,
        scroll_percent=scroll_percent,
        engaged_seconds=engaged_seconds,
        properties=properties or {},
    )
