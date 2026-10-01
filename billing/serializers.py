from django.db import IntegrityError
from django.utils import timezone
from rest_framework import serializers
from .models import IssuerProfile, Client, Document, Condition


class IssuerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = IssuerProfile
        fields = [
            'legal_name', 'tax_id', 'address', 'phone', 'website', 'email',
            'city', 'iban', 'quote_conditions', 'updated_at',
        ]
        read_only_fields = ['updated_at']


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            'id', 'name', 'tax_id', 'address', 'email',
            'authorization_text', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Condition
        fields = ['id', 'title', 'text', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class DocumentSerializer(serializers.ModelSerializer):
    # Optional on create: defaults to today / date.year / next free sequence
    date = serializers.DateField(required=False)
    year = serializers.IntegerField(required=False, min_value=1)
    sequence = serializers.IntegerField(required=False, min_value=1)
    client = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        required=False,
        allow_null=True,
    )
    source_quote = serializers.PrimaryKeyRelatedField(
        queryset=Document.objects.filter(kind=Document.KIND_QUOTE),
        required=False,
        allow_null=True,
    )

    number = serializers.CharField(read_only=True)
    client_name = serializers.SerializerMethodField(read_only=True)
    source_quote_number = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Document
        fields = [
            'id',
            'kind', 'year', 'sequence', 'number', 'date', 'status',
            'client', 'client_name', 'client_snapshot',
            'layout', 'content',
            'iva_rate', 'irpf_rate', 'totals_style',
            'authorization_text', 'conditions_text', 'payment_text',
            'base_amount', 'iva_amount', 'irpf_amount', 'total_amount',
            'source_quote', 'source_quote_number',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'number', 'client_name', 'source_quote_number', 'created_at', 'updated_at']
        # (kind, year, sequence) uniqueness is checked in validate() so year/sequence can stay optional
        validators = []

    def get_client_name(self, obj):
        snapshot = obj.client_snapshot if isinstance(obj.client_snapshot, dict) else {}
        return snapshot.get('name') or None

    def get_source_quote_number(self, obj):
        return obj.source_quote.number if obj.source_quote_id else None

    # ---------- validation ----------
    def validate_client_snapshot(self, value):
        if value in (None, ''):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("client_snapshot must be an object.")
        return value

    def validate_content(self, value):
        return value if value is not None else {}

    def validate(self, attrs):
        instance = self.instance

        if instance is None:
            if not attrs.get('date'):
                attrs['date'] = timezone.localdate()
            if not attrs.get('year'):
                attrs['year'] = attrs['date'].year

        kind = attrs.get('kind', instance.kind if instance else None)
        year = attrs.get('year', instance.year if instance else None)
        sequence = attrs.get('sequence', instance.sequence if instance else None)

        if kind and year and sequence:
            taken = Document.objects.filter(kind=kind, year=year, sequence=sequence)
            if instance is not None:
                taken = taken.exclude(pk=instance.pk)
            if taken.exists():
                number = f"{year % 100:02d}/{sequence:02d}"
                raise serializers.ValidationError({
                    'sequence': [f"Number {number} is already used by another {kind} of {year}."]
                })

        # Freeze the client data printed on the PDF
        client = attrs.get('client')
        if client and not attrs.get('client_snapshot'):
            attrs['client_snapshot'] = client.snapshot()

        return attrs

    # ---------- create / update ----------
    def _duplicate_number_error(self):
        return serializers.ValidationError({
            'sequence': ["This number is already used by another document of the same kind and year."]
        })

    def create(self, validated_data):
        try:
            return Document.create_numbered(**validated_data)
        except IntegrityError:
            raise self._duplicate_number_error()

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except IntegrityError:
            raise self._duplicate_number_error()
