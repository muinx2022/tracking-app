import json
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from analytics.models import Event
from analytics.stats import kpi_comparison, period_bounds, project_stats
from core.forms import ProjectForm
from core.models import Project


class HomeView(View):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("user_dashboard")
        return redirect("user_login")


class DashboardView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "core/dashboard.html"
    context_object_name = "projects"

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        projects = list(ctx["projects"])
        if not projects:
            return ctx
        since = timezone.now() - timedelta(days=7)
        ids = [p.pk for p in projects]
        counts = (
            Event.objects.filter(
                project_id__in=ids,
                occurred_at__gte=since,
                event_type=Event.EventType.PAGEVIEW,
            )
            .values("project_id")
            .annotate(pv=Count("id"))
        )
        by_id = {row["project_id"]: row["pv"] for row in counts}
        for p in projects:
            p.pageviews_7d = by_id.get(p.pk, 0)
        ctx["projects"] = projects
        return ctx


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "core/project_form.html"
    success_url = reverse_lazy("user_dashboard")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = "core/project_form.html"
    success_url = reverse_lazy("user_dashboard")

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = "Edit project"
        ctx["submit_label"] = "Save changes"
        return ctx


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = "core/project_confirm_delete.html"
    success_url = reverse_lazy("user_dashboard")

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)


class ProjectDetailView(LoginRequiredMixin, TemplateView):
    template_name = "core/project_detail.html"
    partial_template_name = "core/partials/project_stats.html"

    def get_project(self):
        return get_object_or_404(
            Project.objects.filter(owner=self.request.user),
            pk=self.kwargs["pk"],
        )

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return [self.partial_template_name]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.get_project()
        period = self.request.GET.get("period", "7d")
        if period not in ("7d", "30d", "today"):
            period = "7d"
        start, end = period_bounds(period)
        stats = project_stats(project, start, end)
        kpi = kpi_comparison(project, period)

        traffic_labels = []
        traffic_values = []
        for row in stats["traffic_by_day"]:
            day = row["day"]
            traffic_labels.append(day.isoformat() if hasattr(day, "isoformat") else str(day))
            traffic_values.append(row["views"])

        device_labels = [r["visitor__device"] or "unknown" for r in stats["device_breakdown"]]
        device_values = [r["count"] for r in stats["device_breakdown"]]

        os_labels = [r["visitor__os"] or "unknown" for r in stats["os_breakdown"]]
        os_values = [r["count"] for r in stats["os_breakdown"]]

        browser_labels = [r["visitor__browser"] or "unknown" for r in stats["browser_breakdown"]]
        browser_values = [r["count"] for r in stats["browser_breakdown"]]

        ctx.update(
            {
                "project": project,
                "period": period,
                "pageviews": stats["pageviews"],
                "unique_visitors": stats["unique_visitors"],
                "total_sessions": stats["total_sessions"],
                "bounce_rate": stats["bounce_rate"],
                "top_pages": stats["top_pages"],
                "top_referrers": stats["top_referrers"],
                "traffic_chart": json.dumps(
                    {"labels": traffic_labels, "values": traffic_values}
                ),
                "device_chart": json.dumps(
                    {"labels": device_labels, "values": device_values}
                ),
                "os_chart": json.dumps({"labels": os_labels, "values": os_values}),
                "browser_chart": json.dumps(
                    {"labels": browser_labels, "values": browser_values}
                ),
                **kpi,
            }
        )
        return ctx


class TrackTestView(LoginRequiredMixin, TemplateView):
    """Minimal page with tracker.js embedded (same-origin) for manual QA."""

    template_name = "core/track_test.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = get_object_or_404(
            Project.objects.filter(owner=self.request.user),
            pk=self.kwargs["pk"],
        )
        return ctx
