import json
from datetime import date, timedelta

from django.conf import settings
from rest_framework import status
from rest_framework.parsers import BaseParser, JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import geo, tracking
from .net import ClientIPScopedThrottle, client_ip
from .models import AnalyticsSettings
from .report import build_report

SECTIONS = (
    "kpis", "timeline", "projects", "pages", "sources", "contact", "countries",
    "devices", "clicks", "interest", "entry_exit", "when", "not_found",
)

class PlainTextJSONParser(BaseParser):
    """Visits arrive as text/plain JSON so the browser can send them without a CORS preflight."""
    media_type = "text/plain"

    def parse(self, stream, media_type=None, parser_context=None):
        try:
            return json.loads(stream.read().decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            return {}


def visitor_origin(request) -> tuple[str, str]:
    """The visitor's IP (never stored) and its country, looked up on this server."""
    ip, _ = client_ip(request)
    return ip, geo.country_of(ip)


class CollectView(APIView):
    """
    Endpoint (public):
    - POST /v/  → {t: "pageview" | "leave" | "event", ...}  (a neutral name, so blockers leave it alone)
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [PlainTextJSONParser, JSONParser]
    throttle_classes = [ClientIPScopedThrottle]
    throttle_scope = "analytics"

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        user_agent = request.headers.get("User-Agent", "")[:400]
        if tracking.is_bot(user_agent):
            return Response(status=status.HTTP_204_NO_CONTENT)
        ip, country = visitor_origin(request)
        kind = data.get("t")
        if kind == "pageview":
            pageview = tracking.record_pageview(ip, user_agent, country, data)
            return Response({"id": pageview.id}, status=status.HTTP_201_CREATED)
        if kind == "leave":
            tracking.record_leave(ip, user_agent, data)
        elif kind == "event":
            tracking.record_event(ip, user_agent, data)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _parse_day(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


class ReportView(APIView):
    """
    Endpoint (private):
    - GET /analytics/report/?from=YYYY-MM-DD&to=YYYY-MM-DD  → Everything the statistics page shows
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        end = _parse_day(request.query_params.get("to")) or tracking.today()
        start = _parse_day(request.query_params.get("from")) or end - timedelta(days=29)
        if start > end:
            start, end = end, start
        start = max(start, end - timedelta(days=settings.ANALYTICS_RETENTION_DAYS))
        return Response(build_report(start, end))


class SettingsView(APIView):
    """
    Endpoints (private):
    - GET /analytics/settings/  → {hidden_sections: [...]}
    - PUT /analytics/settings/  → Save which sections are hidden
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"hidden_sections": AnalyticsSettings.load().hidden_sections, "sections": SECTIONS})

    def put(self, request):
        hidden = request.data.get("hidden_sections")
        if not isinstance(hidden, list) or any(item not in SECTIONS for item in hidden):
            return Response({"hidden_sections": "Unknown section."}, status=status.HTTP_400_BAD_REQUEST)
        settings_record = AnalyticsSettings.load()
        settings_record.hidden_sections = [s for s in SECTIONS if s in hidden]
        settings_record.save(update_fields=["hidden_sections"])
        return Response({"hidden_sections": settings_record.hidden_sections, "sections": SECTIONS})


class ConnectionView(APIView):
    """
    Endpoint (private):
    - GET /analytics/connection/  → The country of the signed-in person's own connection, and which
      header the IP was read from, so it can be checked that visits are located correctly.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ip, source = client_ip(request)
        return Response({"country": geo.country_of(ip), "source": source})
