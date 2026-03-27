import json
import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from analytics.models import Event, TrackingSession, Visitor
from core.models import Project


class TrackingApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="owner", password="pass123")
        self.project = Project.objects.create(name="Trekky", owner=self.user, domain="trekky.net")

    def test_track_accepts_content_and_attribution_fields(self):
        payload = {
            "tracking_id": str(self.project.tracking_id),
            "client_id": "client-1",
            "session_id": "session-1",
            "event_type": "custom",
            "event_name": "signup",
            "url": "https://trekky.net/posts/demo?utm_source=facebook",
            "title": "Demo title",
            "referrer": "https://facebook.com/story",
            "page_type": "article",
            "content_id": "post-123",
            "content_slug": "demo-post",
            "content_title": "Demo post",
            "author": "Lan",
            "category": "Travel",
            "tags": ["travel", "sea"],
            "utm_source": "facebook",
            "utm_medium": "social",
            "utm_campaign": "summer",
            "destination_url": "https://trekky.net/signup",
            "cta_name": "signup_cta",
            "scroll_percent": 75,
            "engaged_seconds": 18,
            "properties": {"placement": "hero"},
        }
        response = self.client.post(
            reverse("api_track"),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_USER_AGENT="Mozilla/5.0",
            HTTP_CF_IPCOUNTRY="VN",
        )
        self.assertEqual(response.status_code, 200)
        event = Event.objects.get()
        visitor = Visitor.objects.get()
        session = TrackingSession.objects.get()
        self.assertEqual(event.event_name, "signup")
        self.assertEqual(event.page_type, "article")
        self.assertEqual(event.content_slug, "demo-post")
        self.assertEqual(event.source_group, "Social")
        self.assertEqual(event.campaign, "summer")
        self.assertEqual(event.cta_name, "signup_cta")
        self.assertEqual(event.properties["placement"], "hero")
        self.assertEqual(visitor.country_code, "VN")
        self.assertFalse(visitor.is_bot)
        self.assertEqual(session.landing_page_type, "article")
        self.assertEqual(session.source_group, "Social")

    def test_track_marks_bot_from_user_agent(self):
        payload = {
            "tracking_id": str(self.project.tracking_id),
            "client_id": "bot-1",
            "url": "https://trekky.net/",
        }
        response = self.client.post(
            reverse("api_track"),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_USER_AGENT="Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        )
        self.assertEqual(response.status_code, 200)
        visitor = Visitor.objects.get(client_id="bot-1")
        self.assertTrue(visitor.is_bot)


class TrackingDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="owner", password="pass123")
        self.project = Project.objects.create(name="Trekky", owner=self.user, domain="trekky.net")
        self.client.force_login(self.user)
        self.visitor = Visitor.objects.create(
            project=self.project,
            client_id="human-1",
            browser="Chrome",
            os="MacOS",
            device="desktop",
        )
        self.bot_visitor = Visitor.objects.create(
            project=self.project,
            client_id="bot-1",
            browser="Bot",
            os="Linux",
            device="desktop",
            is_bot=True,
            bot_name="bot",
        )
        self.session = TrackingSession.objects.create(
            project=self.project,
            visitor=self.visitor,
            client_session_id="s1",
            last_activity_at=timezone.now(),
            landing_url="https://trekky.net/posts/1",
            landing_title="Post 1",
            landing_page_type="article",
            landing_category="Travel",
            source_group="Social",
            source_name="facebook.com",
            medium="social",
            campaign="spring",
        )
        self.bot_session = TrackingSession.objects.create(
            project=self.project,
            visitor=self.bot_visitor,
            client_session_id="s2",
            last_activity_at=timezone.now(),
            landing_url="https://trekky.net/bot",
        )
        now = timezone.now()
        Event.objects.create(
            project=self.project,
            visitor=self.visitor,
            session=self.session,
            event_type=Event.EventType.PAGEVIEW,
            event_name="",
            url="https://trekky.net/posts/1",
            title="Post 1",
            referrer="https://facebook.com/story",
            occurred_at=now - timedelta(minutes=5),
            page_type="article",
            content_title="Post 1",
            content_slug="post-1",
            category="Travel",
            source_group="Social",
            source_name="facebook.com",
            medium="social",
            campaign="spring",
        )
        Event.objects.create(
            project=self.project,
            visitor=self.visitor,
            session=self.session,
            event_type=Event.EventType.ENGAGED_VISIT,
            event_name="",
            url="https://trekky.net/posts/1",
            title="Post 1",
            referrer="",
            occurred_at=now - timedelta(minutes=4),
            engaged_seconds=20,
        )
        Event.objects.create(
            project=self.project,
            visitor=self.bot_visitor,
            session=self.bot_session,
            event_type=Event.EventType.PAGEVIEW,
            event_name="",
            url="https://trekky.net/bot",
            title="Bot Page",
            referrer="",
            occurred_at=now - timedelta(minutes=3),
        )

    def test_project_detail_excludes_bots_by_default(self):
        response = self.client.get(reverse("user_project_detail", args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Post 1")
        self.assertNotContains(response, "https://trekky.net/bot")

    def test_project_detail_filters_by_source(self):
        response = self.client.get(
            reverse("user_project_detail", args=[self.project.pk]),
            {"source": "Social", "period": "7d"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Traffic by source")
        self.assertContains(response, "Social")

    def test_export_csv_returns_top_content(self):
        response = self.client.get(
            reverse("user_project_export", args=[self.project.pk]),
            {"period": "7d"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("Post 1", response.content.decode())
