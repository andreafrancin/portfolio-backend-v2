"""Everything the statistics page shows for a range of days.

Visitors are counted once per day (their code changes every day), so totals over several days are
the sum of daily visitors: someone who comes back on another day counts again.
"""
from collections import Counter, defaultdict
from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.utils import timezone

from projects.models import Project

from .models import Event, PageView
from .tracking import MADRID

LIVE_WINDOW = timedelta(minutes=5)
TOP = 12


def _totals(start, end) -> dict:
    views = PageView.objects.filter(day__range=(start, end))
    sessions = views.values("session").annotate(pages=Count("id"))
    session_count = sessions.count()
    single = sessions.filter(pages=1).count()
    durations = views.filter(duration_ms__isnull=False, duration_ms__gt=0).aggregate(avg=Avg("duration_ms"))
    sent = Event.objects.filter(day__range=(start, end), name="contact_sent").values("visitor").distinct().count()
    return {
        "visitors": views.values("visitor").distinct().count(),
        "sessions": session_count,
        "pageviews": views.count(),
        "avg_duration_ms": round(durations["avg"] or 0),
        "bounce_rate": round(single / session_count, 3) if session_count else 0,
        "messages": sent,
    }


def _daily(start, end) -> list:
    rows = {
        row["day"]: row
        for row in PageView.objects.filter(day__range=(start, end))
        .values("day")
        .annotate(
            visitors=Count("visitor", distinct=True),
            sessions=Count("session", distinct=True),
            pageviews=Count("id"),
        )
    }
    out, day = [], start
    while day <= end:
        row = rows.get(day, {})
        out.append({
            "day": day.isoformat(),
            "visitors": row.get("visitors", 0),
            "sessions": row.get("sessions", 0),
            "pageviews": row.get("pageviews", 0),
        })
        day += timedelta(days=1)
    return out


def _grouped(queryset, field, limit=TOP, label_blank=None) -> list:
    rows = (
        queryset.values(field)
        .annotate(visitors=Count("visitor", distinct=True), views=Count("id"))
        .order_by("-visitors", "-views")
    )
    out = []
    for row in rows[:limit]:
        key = row[field]
        if not key and label_blank is None:
            continue
        out.append({"key": key or label_blank, "visitors": row["visitors"], "views": row["views"]})
    return out


def _exit_pages(views) -> list:
    last = {}
    for session, page, path in views.order_by("created_at").values_list("session", "page", "path"):
        last[session] = path if page == "not_found" else page
    counts = Counter(last.values())
    return [{"key": key, "sessions": n} for key, n in counts.most_common(TOP)]


def _projects(views, events) -> list:
    titles = {
        p.id: (p.title_i18n or {}).get("es") or p.title
        for p in Project.objects.only("id", "title", "title_i18n")
    }
    images = Counter(
        events.filter(name="lightbox_open", project_id__isnull=False).values_list("project_id", flat=True)
    )
    rows = (
        views.filter(page="project")
        .values("project_id")
        .annotate(
            visitors=Count("visitor", distinct=True),
            views=Count("id"),
            avg_duration_ms=Avg("duration_ms", filter=Q(duration_ms__gt=0)),
            avg_scroll=Avg("scroll_pct", filter=Q(scroll_pct__isnull=False)),
            read_through=Count("id", filter=Q(scroll_pct__gte=75)),
            measured=Count("id", filter=Q(scroll_pct__isnull=False)),
        )
        .order_by("-visitors", "-views")
    )
    return [
        {
            "id": row["project_id"],
            "title": titles.get(row["project_id"], f"#{row['project_id']}"),
            "visitors": row["visitors"],
            "views": row["views"],
            "avg_duration_ms": round(row["avg_duration_ms"] or 0),
            "avg_scroll": round(row["avg_scroll"] or 0),
            "read_through": round(row["read_through"] / row["measured"], 3) if row["measured"] else None,
            "images_opened": images.get(row["project_id"], 0),
        }
        for row in rows
    ]


def _event_values(events, name, limit=TOP) -> list:
    rows = (
        events.filter(name=name).exclude(value="")
        .values("value").annotate(count=Count("id"), visitors=Count("visitor", distinct=True))
        .order_by("-count")[:limit]
    )
    return [{"key": r["value"], "count": r["count"], "visitors": r["visitors"]} for r in rows]


def _when(views) -> list:
    """Page views by weekday (0 = Monday) and hour, in Spanish time."""
    grid = defaultdict(int)
    for created in views.values_list("created_at", flat=True):
        local = timezone.localtime(created, MADRID)
        grid[(local.weekday(), local.hour)] += 1
    return [[grid[(d, h)] for h in range(24)] for d in range(7)]


def build_report(start, end) -> dict:
    length = (end - start).days + 1
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=length - 1)

    views = PageView.objects.filter(day__range=(start, end))
    events = Event.objects.filter(day__range=(start, end))
    entries = views.filter(is_entry=True)

    contact_visitors = views.filter(page="contact").values("visitor").distinct().count()
    started = events.filter(name="contact_start").values("visitor").distinct().count()
    sent = events.filter(name="contact_sent").values("visitor").distinct().count()

    outbound = Counter(
        events.filter(name__in=["instagram_click", "linkedin_click", "email_click", "copy_email"])
        .values_list("name", flat=True)
    )

    return {
        "range": {"from": start.isoformat(), "to": end.isoformat()},
        "previous_range": {"from": previous_start.isoformat(), "to": previous_end.isoformat()},
        "live": PageView.objects.filter(created_at__gte=timezone.now() - LIVE_WINDOW)
        .values("visitor").distinct().count(),
        "totals": _totals(start, end),
        "previous": _totals(previous_start, previous_end),
        "daily": _daily(start, end),
        "pages": _grouped(views, "page"),
        "entry_pages": _grouped(entries, "page"),
        "exit_pages": _exit_pages(views),
        "not_found": _grouped(views.filter(page="not_found"), "path"),
        "projects": _projects(views, events),
        "sources": _grouped(entries, "source"),
        "referrers": _grouped(entries.exclude(referrer_host=""), "referrer_host"),
        "campaigns": _grouped(entries.exclude(campaign=""), "campaign"),
        "countries": _grouped(views, "country", label_blank="??"),
        "languages": _grouped(views, "language"),
        "devices": _grouped(views, "device"),
        "funnel": {"contact_visitors": contact_visitors, "started": started, "sent": sent},
        "services_chosen": _event_values(events, "contact_sent"),
        "services_opened": _event_values(events, "services_group"),
        "categories": _event_values(events, "filter_category"),
        "outbound": [{"key": k, "count": n} for k, n in outbound.most_common()],
        "suggested_clicks": events.filter(name="suggested_click").count(),
        "when": _when(views),
    }
