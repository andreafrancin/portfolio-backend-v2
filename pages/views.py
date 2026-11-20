# pages/views.py
from django.conf import settings
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from zoneinfo import ZoneInfo

from django.utils import timezone
from . import contact_emails
from .contact_mail import (
    HEADER_CONTENT_ID,
    ContactMailError,
    confirmation_enabled,
    header_image_data_uri,
    send_confirmation,
    send_mail,
)
from .models import About, AutoReply, Contact, Service, ServiceGroup
from .serializers import (
    AboutSerializer,
    AutoReplySerializer,
    ContactMessageSerializer,
    ContactSerializer,
    ServiceGroupSerializer,
    ServiceSerializer,
)


class AboutViewSet(viewsets.ModelViewSet):
    queryset = About.objects.all()
    serializer_class = AboutSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]


def apply_order(model, order_list):
    """Save the position of each id in order_list; returns an error Response or None."""
    if not isinstance(order_list, list):
        return Response({"error": "Field 'order' must be a list of IDs"}, status=status.HTTP_400_BAD_REQUEST)
    items = {item.id: item for item in model.objects.filter(id__in=order_list)}
    if set(order_list) != set(items):
        return Response({"error": "The list of IDs does not match existing items"}, status=status.HTTP_400_BAD_REQUEST)
    with transaction.atomic():
        for idx, item_id in enumerate(order_list):
            items[item_id].order = idx
        model.objects.bulk_update(items.values(), ['order'])
    return None


class ServiceGroupViewSet(viewsets.ModelViewSet):
    """
    Endpoints:
    - GET    /service-groups/          → Groups with their services (public: the services page)
    - POST   /service-groups/          → Create a group
    - PATCH  /service-groups/{id}/     → Rename a group
    - DELETE /service-groups/{id}/     → Remove a group and its services
    - POST   /service-groups/reorder/  → Change the order of the groups
    """
    queryset = ServiceGroup.objects.prefetch_related('services')
    serializer_class = ServiceGroupSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['post'])
    def reorder(self, request):
        error = apply_order(ServiceGroup, request.data.get('order'))
        return error or Response({"status": "Order updated."})


class ServiceViewSet(viewsets.ModelViewSet):
    """
    Endpoints:
    - POST   /services/          → Create a service inside a group
    - PATCH  /services/{id}/     → Modify a service
    - DELETE /services/{id}/     → Remove a service
    - POST   /services/reorder/  → Change the order of the services of one group
    """
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['post'])
    def reorder(self, request):
        error = apply_order(Service, request.data.get('order'))
        return error or Response({"status": "Order updated."})



def known_service_names() -> set[str]:
    """Service names in every language: only these are repeated back to the visitor."""
    names = set()
    for service in Service.objects.only('name_i18n'):
        names.update(v for v in (service.name_i18n or {}).values() if v)
    return names


class ContactMessageView(APIView):
    """
    Endpoint:
    - POST /contact-messages/  → Email a message from the public contact form to the site owner
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'contact'

    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # A filled honeypot means a bot: answer as if it worked and send nothing.
        if data.get('website'):
            return Response({"status": "sent"}, status=status.HTTP_201_CREATED)

        sent_at = timezone.localtime(timezone=ZoneInfo('Europe/Madrid')).strftime('%d/%m/%Y %H:%M')
        subject, text, html = contact_emails.render_notification(data, sent_at)
        try:
            send_mail(settings.CONTACT_RECIPIENT, subject, text, reply_to=data['email'], html=html)
        except ContactMailError:
            return Response(
                {"error": "The message could not be sent."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        auto_reply = AutoReply.load()
        if auto_reply.enabled and confirmation_enabled():
            known_service = data.get('service') if data.get('service') in known_service_names() else None
            texts = contact_emails.auto_reply_texts(saved_texts(auto_reply), data['language'])
            send_confirmation(
                data['email'],
                *contact_emails.render_confirmation(data['language'], data['name'], known_service, texts),
            )
        return Response({"status": "sent"}, status=status.HTTP_201_CREATED)


def saved_texts(source) -> dict:
    """The per-language texts of an AutoReply, or of a draft sent by the back office, keyed by field."""
    get = source.get if isinstance(source, dict) else lambda key, default=None: getattr(source, key, default)
    return {field: get(f'{field}_i18n') or {} for field in contact_emails.AUTO_REPLY_FIELDS}


def sample_service(language: str) -> str | None:
    service = Service.objects.order_by('group__order', 'order', 'id').first()
    if not service:
        return None
    names = service.name_i18n or {}
    return names.get(language) or names.get('es') or next(iter(names.values()), None)


class AutoReplyView(APIView):
    """
    Endpoints (private):
    - GET /auto-reply/  → The confirmation sent to visitors, with the built-in texts as defaults
    - PUT /auto-reply/  → Save it
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(AutoReplySerializer(AutoReply.load()).data)

    def put(self, request):
        serializer = AutoReplySerializer(AutoReply.load(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AutoReplyDraftMixin:
    def render_draft(self, request, preview_image: bool):
        serializer = AutoReplySerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        language = request.data.get('language') if request.data.get('language') in ('es', 'ca', 'en') else 'es'
        texts = contact_emails.auto_reply_texts(saved_texts(serializer.validated_data), language)
        subject, text, html = contact_emails.render_confirmation(
            language, 'Laura', sample_service(language), texts
        )
        if preview_image:
            html = html.replace(f'cid:{HEADER_CONTENT_ID}', header_image_data_uri())
        return subject, text, html


class AutoReplyPreviewView(AutoReplyDraftMixin, APIView):
    """POST /auto-reply/preview/ → The email as a visitor called Laura would receive it, with unsaved changes."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        subject, _, html = self.render_draft(request, preview_image=True)
        return Response({"subject": subject, "html": html})


class AutoReplyTestView(AutoReplyDraftMixin, APIView):
    """POST /auto-reply/test/ → Send the draft to the site owner's own inbox."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        subject, text, html = self.render_draft(request, preview_image=False)
        try:
            send_mail(settings.CONTACT_RECIPIENT, f"[Prueba] {subject}"[:150], text, settings.CONTACT_REPLY_TO, html)
        except ContactMailError:
            return Response({"error": "The test could not be sent."}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({"status": "sent", "to": settings.CONTACT_RECIPIENT})
