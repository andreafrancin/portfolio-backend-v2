from django.db import IntegrityError
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import IssuerProfile, Client, Condition, Document
from .serializers import (
    IssuerProfileSerializer,
    ClientSerializer,
    ConditionSerializer,
    DocumentSerializer,
)


# All billing endpoints use the default permissions (JWT + IsAuthenticated): private data.


class IssuerProfileView(APIView):
    """
    Endpoints:
    - GET   /billing/issuer/   → Get the issuer profile (created on first access)
    - PUT   /billing/issuer/   → Replace the issuer profile
    - PATCH /billing/issuer/   → Partially update the issuer profile
    """
    def get(self, request):
        serializer = IssuerProfileSerializer(IssuerProfile.get_solo())
        return Response(serializer.data)

    def put(self, request):
        return self._update(request, partial=False)

    def patch(self, request):
        return self._update(request, partial=True)

    def _update(self, request, partial):
        serializer = IssuerProfileSerializer(IssuerProfile.get_solo(), data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ClientViewSet(viewsets.ModelViewSet):
    """
    Endpoints:
    - GET    /billing/clients/?search=   → List clients (search on name)
    - GET    /billing/clients/{id}/      → Get a client
    - POST   /billing/clients/           → Create a client
    - PUT    /billing/clients/{id}/      → Modify a client
    - DELETE /billing/clients/{id}/      → Remove a client (its documents are kept)
    """
    serializer_class = ClientSerializer

    def get_queryset(self):
        qs = Client.objects.all()
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(name__icontains=search)
        return qs


class ConditionViewSet(viewsets.ModelViewSet):
    """
    Endpoints:
    - GET    /billing/conditions/        → List saved conditions
    - POST   /billing/conditions/        → Create one
    - PUT    /billing/conditions/{id}/   → Modify one
    - DELETE /billing/conditions/{id}/   → Remove one (documents keep their own copy of the text)
    """
    serializer_class = ConditionSerializer
    queryset = Condition.objects.all()


class DocumentViewSet(viewsets.ModelViewSet):
    """
    Endpoints:
    - GET    /billing/documents/?kind=&year=&client=&search=   → List documents
    - GET    /billing/documents/{id}/                          → Get a document
    - POST   /billing/documents/                               → Create (sequence/year/date optional)
    - PUT    /billing/documents/{id}/                          → Modify a document
    - DELETE /billing/documents/{id}/                          → Remove a document
    - GET    /billing/documents/next-number/?kind=&year=       → Next free number of a series
    - POST   /billing/documents/{id}/duplicate/                → Copy as a new draft (current year)
    - POST   /billing/documents/{id}/to-invoice/               → Create an invoice from a quote
    """
    serializer_class = DocumentSerializer

    def get_queryset(self):
        qs = Document.objects.select_related('source_quote')
        params = self.request.query_params

        kind = params.get('kind')
        if kind:
            qs = qs.filter(kind=kind)
        year = params.get('year')
        if year and year.isdigit():
            qs = qs.filter(year=int(year))
        client = params.get('client')
        if client and client.isdigit():
            qs = qs.filter(client_id=int(client))
        search = params.get('search')
        if search:
            qs = qs.filter(client_snapshot__name__icontains=search)
        return qs

    def _created(self, document):
        serializer = self.get_serializer(document)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='next-number')
    def next_number(self, request):
        kind = request.query_params.get('kind', Document.KIND_QUOTE)
        if kind not in dict(Document.KIND_CHOICES):
            return Response(
                {"error": "Field 'kind' must be 'quote' or 'invoice'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        year = request.query_params.get('year')
        if year is None or year == '':
            year = timezone.localdate().year
        elif year.isdigit():
            year = int(year)
        else:
            return Response(
                {"error": "Field 'year' must be a full year, e.g. 2026"},
                status=status.HTTP_400_BAD_REQUEST
            )

        sequence = Document.next_sequence(kind, year)
        return Response({
            'kind': kind,
            'year': year,
            'sequence': sequence,
            'number': f"{year % 100:02d}/{sequence:02d}",
        })

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        original = self.get_object()
        today = timezone.localdate()
        try:
            copy = Document.create_numbered(
                kind=original.kind,
                year=today.year,
                date=today,
                status='draft',
                client=original.client,
                client_snapshot=original.client_snapshot,
                layout=original.layout,
                content=original.content,
                iva_rate=original.iva_rate,
                irpf_rate=original.irpf_rate,
                totals_style=original.totals_style,
                authorization_text=original.authorization_text,
                conditions_text=original.conditions_text,
                payment_text=original.payment_text,
                base_amount=original.base_amount,
                iva_amount=original.iva_amount,
                irpf_amount=original.irpf_amount,
                total_amount=original.total_amount,
                source_quote=original.source_quote,
            )
        except IntegrityError:
            return Response({"error": "Could not assign a number, try again"}, status=status.HTTP_409_CONFLICT)
        return self._created(copy)

    @action(detail=True, methods=['post'], url_path='to-invoice')
    def to_invoice(self, request, pk=None):
        quote = self.get_object()
        if quote.kind != Document.KIND_QUOTE:
            return Response(
                {"error": "Only quotes can be converted into invoices"},
                status=status.HTTP_400_BAD_REQUEST
            )

        today = timezone.localdate()
        issuer = IssuerProfile.get_solo()
        try:
            invoice = Document.create_numbered(
                kind=Document.KIND_INVOICE,
                year=today.year,
                date=today,
                status='draft',
                client=quote.client,
                client_snapshot=quote.client_snapshot,
                layout='invoice',
                content=quote.content,
                iva_rate=quote.iva_rate,
                irpf_rate=quote.irpf_rate,
                totals_style='table',
                payment_text=issuer.iban,
                base_amount=quote.base_amount,
                iva_amount=quote.iva_amount,
                irpf_amount=quote.irpf_amount,
                total_amount=quote.total_amount,
                source_quote=quote,
            )
        except IntegrityError:
            return Response({"error": "Could not assign a number, try again"}, status=status.HTTP_409_CONFLICT)
        return self._created(invoice)
