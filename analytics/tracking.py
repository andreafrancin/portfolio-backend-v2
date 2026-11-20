"""Turn an incoming visit into an anonymous record.

A visitor is a code made from the IP address, the browser and a secret that changes every day. The
same person counts once per day, nothing is stored on their device, the IP itself is never saved,
and once a day's secret is deleted that day's codes can no longer be linked to anyone.
"""
import hashlib
import re
import secrets
from datetime import timedelta
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import DailySalt, Event, PageView

MADRID = ZoneInfo("Europe/Madrid")
SESSION_GAP = timedelta(minutes=30)

PAGES = {"/": "work", "/work": "work", "/services": "services", "/about": "about",
         "/contact": "contact", "/legal": "legal"}
PROJECT_PATH = re.compile(r"^/work/(\d{1,9})$")

EVENTS = {
    "contact_start", "contact_sent", "copy_email", "email_click", "instagram_click",
    "linkedin_click", "lightbox_open", "filter_category", "services_group", "suggested_click",
}

BOT_PATTERN = re.compile(
    r"bot|crawl|spider|slurp|headless|lighthouse|preview|facebookexternalhit|embedly|"
    r"python-requests|curl|wget|httpclient|phantomjs|puppeteer|playwright",
    re.IGNORECASE,
)

SOURCES = [
    ("instagram", "Instagram"), ("linkedin", "LinkedIn"), ("lnkd.in", "LinkedIn"),
    ("google.", "Google"), ("bing.", "Bing"), ("duckduckgo", "DuckDuckGo"), ("ecosia", "Ecosia"),
    ("yahoo.", "Yahoo"), ("facebook", "Facebook"), ("fb.", "Facebook"), ("behance", "Behance"),
    ("pinterest", "Pinterest"), ("t.co", "X"), ("twitter", "X"), ("x.com", "X"),
    ("tiktok", "TikTok"), ("youtube", "YouTube"), ("whatsapp", "WhatsApp"), ("dribbble", "Dribbble"),
    ("chatgpt", "ChatGPT"), ("perplexity", "Perplexity"),
]
OWN_HOSTS = ("andreafrancin.com", "localhost", "127.0.0.1")


def today():
    return timezone.localtime(timezone=MADRID).date()


def is_bot(user_agent: str) -> bool:
    return not user_agent or bool(BOT_PATTERN.search(user_agent))


def device_of(user_agent: str) -> str:
    ua = user_agent.lower()
    if "ipad" in ua or "tablet" in ua or ("android" in ua and "mobile" not in ua):
        return "tablet"
    if "mobi" in ua or "iphone" in ua or "android" in ua:
        return "mobile"
    return "desktop"


def _salt_for(day) -> str:
    salt = DailySalt.objects.filter(day=day).values_list("salt", flat=True).first()
    if salt:
        return salt
    with transaction.atomic():
        record, created = DailySalt.objects.get_or_create(day=day, defaults={"salt": secrets.token_hex(32)})
    if created:
        _forget_the_past(day)
    return record.salt


def _forget_the_past(day) -> None:
    """A new day: yesterday's secret goes, and visits older than the retention period are removed."""
    DailySalt.objects.filter(day__lt=day).delete()
    limit = day - timedelta(days=settings.ANALYTICS_RETENTION_DAYS)
    PageView.objects.filter(day__lt=limit).delete()
    Event.objects.filter(day__lt=limit).delete()


def visitor_code(ip: str, user_agent: str, day) -> str:
    digest = hashlib.sha256(f"{_salt_for(day)}|{ip}|{user_agent}".encode()).hexdigest()
    return digest[:24]


def classify(path: str) -> tuple[str, str, int | None]:
    """Return the clean path, the kind of page and, for a project, its id."""
    clean = (path or "/").split("?")[0].split("#")[0][:255].rstrip("/") or "/"
    if clean in PAGES:
        return clean, PAGES[clean], None
    match = PROJECT_PATH.match(clean)
    if match:
        from projects.models import Project
        project_id = int(match.group(1))
        if Project.objects.filter(id=project_id, hidden=False).exists():
            return clean, "project", project_id
    return clean, "not_found", None


def source_of(referrer: str, utm_source: str) -> tuple[str, str]:
    """Where a visit came from: a tagged campaign source, a known site, another site, or direct."""
    host = ""
    if referrer:
        try:
            host = (urlparse(referrer).hostname or "").lower().removeprefix("www.")[:120]
        except ValueError:
            host = ""
    if host and any(host == own or host.endswith("." + own) for own in OWN_HOSTS):
        host = ""
    if utm_source:
        tag = utm_source.strip().lower()[:60]
        for needle, name in SOURCES:
            if needle.rstrip(".") == tag:
                return name, host
        return tag, host
    if not host:
        return "Direct", ""
    for needle, name in SOURCES:
        if needle in host:
            return name, host
    return host, host


def current_session(visitor: str, now) -> tuple[str, bool]:
    """The visit continues while pages are seen less than 30 minutes apart."""
    last = (
        PageView.objects.filter(visitor=visitor, created_at__gte=now - SESSION_GAP)
        .order_by("-created_at")
        .values_list("session", flat=True)
        .first()
    )
    if last:
        return last, False
    return secrets.token_hex(8), True


def record_pageview(ip, user_agent, country, data) -> PageView | None:
    path, page, project_id = classify(str(data.get("path", "")))
    day = today()
    now = timezone.now()
    visitor = visitor_code(ip, user_agent, day)
    session, is_entry = current_session(visitor, now)
    source, host, campaign = "", "", ""
    if is_entry:
        source, host = source_of(str(data.get("referrer", ""))[:500], str(data.get("utm_source", "")))
        campaign = str(data.get("utm_campaign", "")).strip()[:80]
    language = str(data.get("language", ""))[:5]
    return PageView.objects.create(
        day=day, visitor=visitor, session=session, path=path, page=page, project_id=project_id,
        is_entry=is_entry, source=source, referrer_host=host, campaign=campaign,
        country=country, language=language if language in ("es", "ca", "en") else "",
        device=device_of(user_agent),
    )


def record_leave(ip, user_agent, data) -> None:
    """When a page is left: how long it was really in view and how far down it was read."""
    try:
        pageview_id = int(data.get("id"))
        duration = max(0, min(int(data.get("duration", 0)), 30 * 60 * 1000))
        scroll = max(0, min(int(data.get("scroll", 0)), 100))
    except (TypeError, ValueError):
        return
    day = today()
    visitor = visitor_code(ip, user_agent, day)
    PageView.objects.filter(id=pageview_id, visitor=visitor, day=day).update(
        duration_ms=duration, scroll_pct=scroll
    )


def record_event(ip, user_agent, data) -> None:
    name = str(data.get("name", ""))
    if name not in EVENTS:
        return
    path, _, project_id = classify(str(data.get("path", "")))
    day = today()
    visitor = visitor_code(ip, user_agent, day)
    session, _ = current_session(visitor, timezone.now())
    Event.objects.create(
        day=day, visitor=visitor, session=session, name=name,
        value=str(data.get("value", "")).strip()[:160], path=path, project_id=project_id,
    )
