import json
import uuid
from datetime import datetime

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from analytics.services import (
    classify_source,
    detect_bot,
    get_client_ip,
    get_country,
    parse_ua,
    record_event,
    resolve_session,
    upsert_visitor,
)
from core.models import Project


@csrf_exempt
@require_POST
def track(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "invalid_json"}, status=400)

    tracking_id = payload.get("tracking_id")
    client_id = (payload.get("client_id") or "").strip()
    if not tracking_id or not client_id:
        return JsonResponse({"error": "tracking_id_and_client_id_required"}, status=400)

    try:
        tid = uuid.UUID(str(tracking_id))
    except ValueError:
        return JsonResponse({"error": "invalid_tracking_id"}, status=400)

    try:
        project = Project.objects.get(tracking_id=tid, is_active=True)
    except Project.DoesNotExist:
        return JsonResponse({"error": "unknown_project"}, status=404)

    ua_string = request.META.get("HTTP_USER_AGENT", "")
    browser, os_name, device = parse_ua(ua_string)
    is_bot, bot_name = detect_bot(ua_string)
    ip = get_client_ip(request)
    country_code, country_name = get_country(request)

    visitor = upsert_visitor(
        project,
        client_id,
        browser,
        os_name,
        device,
        ip,
        country_code,
        country_name,
        is_bot,
        bot_name,
    )

    event_type = payload.get("event_type") or "pageview"
    if event_type not in (
        "pageview",
        "click",
        "page_exit",
        "scroll_depth",
        "engaged_visit",
        "cta_click",
        "custom",
    ):
        event_type = "pageview"

    url = (payload.get("url") or "")[:8000]
    if not url:
        return JsonResponse({"error": "url_required"}, status=400)

    title = (payload.get("title") or "")[:512]
    referrer = (payload.get("referrer") or "")[:8000]
    event_name = (payload.get("event_name") or "")[:128]
    page_type = (payload.get("page_type") or "")[:64]
    content_id = (payload.get("content_id") or "")[:128]
    content_slug = (payload.get("content_slug") or "")[:255]
    content_title = (payload.get("content_title") or "")[:512]
    author = (payload.get("author") or "")[:255]
    category = (payload.get("category") or "")[:255]

    tags = payload.get("tags") or []
    if not isinstance(tags, list):
        tags = []
    tags = [str(tag)[:64] for tag in tags[:20] if str(tag).strip()]

    utm_source = (payload.get("utm_source") or "")[:255]
    utm_medium = (payload.get("utm_medium") or "")[:255]
    utm_campaign = (payload.get("utm_campaign") or "")[:255]
    utm_content = (payload.get("utm_content") or "")[:255]
    utm_term = (payload.get("utm_term") or "")[:255]
    source_group, source_name, medium = classify_source(referrer, utm_source, utm_medium)
    campaign = utm_campaign
    destination_url = (payload.get("destination_url") or "")[:8000]
    cta_name = (payload.get("cta_name") or "")[:255]

    scroll_percent = payload.get("scroll_percent")
    try:
        scroll_percent = int(scroll_percent) if scroll_percent is not None else None
    except (TypeError, ValueError):
        scroll_percent = None

    engaged_seconds = payload.get("engaged_seconds")
    try:
        engaged_seconds = int(engaged_seconds) if engaged_seconds is not None else None
    except (TypeError, ValueError):
        engaged_seconds = None

    properties = payload.get("properties") or {}
    if not isinstance(properties, dict):
        properties = {}

    session = resolve_session(
        project,
        visitor,
        str(payload.get("session_id") or ""),
        landing_url=url,
        landing_title=title,
        landing_page_type=page_type,
        landing_category=category,
        source_group=source_group,
        source_name=source_name,
        medium=medium,
        campaign=campaign,
        referrer_domain=source_name if source_group in ("Referral", "Organic Search", "Social") else "",
    )

    occurred_raw = payload.get("occurred_at")
    if occurred_raw:
        try:
            occurred_at = datetime.fromisoformat(
                str(occurred_raw).replace("Z", "+00:00")
            )
            if timezone.is_naive(occurred_at):
                occurred_at = timezone.make_aware(
                    occurred_at,
                    timezone.get_current_timezone(),
                )
        except (ValueError, TypeError):
            occurred_at = timezone.now()
    else:
        occurred_at = timezone.now()

    sw = payload.get("screen_width")
    sh = payload.get("screen_height")
    try:
        screen_width = int(sw) if sw is not None else None
    except (TypeError, ValueError):
        screen_width = None
    try:
        screen_height = int(sh) if sh is not None else None
    except (TypeError, ValueError):
        screen_height = None

    language = (payload.get("language") or "")[:32]

    record_event(
        project,
        visitor,
        session,
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
        tags=tags,
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
        properties=properties,
    )

    return JsonResponse({"ok": True})
