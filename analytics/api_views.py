import json
import uuid
from datetime import datetime

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from analytics.services import (
    get_client_ip,
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
    ip = get_client_ip(request)

    visitor = upsert_visitor(
        project,
        client_id,
        browser,
        os_name,
        device,
        ip,
    )
    session = resolve_session(
        project,
        visitor,
        str(payload.get("session_id") or ""),
    )

    event_type = payload.get("event_type") or "pageview"
    if event_type not in ("pageview", "click"):
        event_type = "pageview"

    url = (payload.get("url") or "")[:8000]
    if not url:
        return JsonResponse({"error": "url_required"}, status=400)

    title = (payload.get("title") or "")[:512]
    referrer = (payload.get("referrer") or "")[:8000]

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
    )

    return JsonResponse({"ok": True})
