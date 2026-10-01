from django.db import models, transaction, IntegrityError


class IssuerProfile(models.Model):
    """Single row (pk=1) with the issuer data printed on quotes and invoices."""
    legal_name = models.CharField(max_length=255, blank=True, default='')
    tax_id = models.CharField(max_length=64, blank=True, default='')
    # One line, e.g. "Carrer de la Cala Crancs, 11, C5 · 43840 Salou · Tarragona, Espanya"
    address = models.CharField(max_length=500, blank=True, default='')
    phone = models.CharField(max_length=64, blank=True, default='')
    website = models.CharField(max_length=255, blank=True, default='')
    email = models.CharField(max_length=255, blank=True, default='')
    # Place printed before the date, e.g. "Salou"
    city = models.CharField(max_length=128, blank=True, default='')
    iban = models.CharField(max_length=64, blank=True, default='')
    # "Condicions" paragraph printed at the bottom of quotes
    quote_conditions = models.TextField(blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.legal_name or 'Issuer profile'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Client(models.Model):
    name = models.CharField(max_length=255)
    tax_id = models.CharField(max_length=64, blank=True, default='')
    address = models.TextField(blank=True, default='')
    email = models.CharField(max_length=255, blank=True, default='')
    # Optional paragraph printed under totals on quotes
    authorization_text = models.TextField(blank=True, default='')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', 'id']

    def __str__(self):
        return self.name

    def snapshot(self):
        return {'name': self.name, 'tax_id': self.tax_id, 'address': self.address}


class Condition(models.Model):
    """A reusable conditions paragraph for quotes ("Condicions"), picked in the editor."""
    title = models.CharField(max_length=255)
    text = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title', 'id']

    def __str__(self):
        return self.title


class Document(models.Model):
    KIND_QUOTE = 'quote'
    KIND_INVOICE = 'invoice'
    KIND_CHOICES = [
        (KIND_QUOTE, 'Quote'),
        (KIND_INVOICE, 'Invoice'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ]

    LAYOUT_CHOICES = [
        ('concept', 'Concept + tax table'),
        ('numbered', 'Numbered items + summary'),
        ('invoice', 'Invoice'),
    ]

    TOTALS_STYLE_CHOICES = [
        ('table', 'Table'),
        ('summary', 'Summary'),
        ('base', 'Base only'),
    ]

    kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    year = models.PositiveIntegerField()
    sequence = models.PositiveIntegerField()
    date = models.DateField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='draft')

    client = models.ForeignKey(
        Client,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='documents',
    )
    # Client data printed on the PDF, frozen when the document is created
    client_snapshot = models.JSONField(default=dict, blank=True)

    layout = models.CharField(max_length=16, choices=LAYOUT_CHOICES, default='concept')
    # Free structure owned by the frontend (intro, sections, lines)
    content = models.JSONField(default=dict, blank=True)

    iva_rate = models.DecimalField(max_digits=5, decimal_places=2, default=21)
    irpf_rate = models.DecimalField(max_digits=5, decimal_places=2, default=15)
    totals_style = models.CharField(max_length=16, choices=TOTALS_STYLE_CHOICES, default='table')

    authorization_text = models.TextField(blank=True, default='')
    conditions_text = models.TextField(blank=True, default='')
    payment_text = models.TextField(blank=True, default='')

    # Computed by the frontend and sent on save; used for listings
    base_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    iva_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    irpf_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Invoice created from a quote
    source_quote = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='invoices',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-year', '-sequence']
        unique_together = [('kind', 'year', 'sequence')]

    def __str__(self):
        return f"{self.get_kind_display()} {self.number}"

    @property
    def number(self):
        return f"{self.year % 100:02d}/{self.sequence:02d}"

    @classmethod
    def next_sequence(cls, kind, year, lock=False):
        qs = cls.objects.filter(kind=kind, year=year)
        if lock:
            # Lock existing rows of this series until the end of the transaction
            list(qs.select_for_update().values_list('id', flat=True))
        last = qs.aggregate(m=models.Max('sequence'))['m']
        return (last or 0) + 1

    @classmethod
    def create_numbered(cls, attempts=5, **fields):
        """
        Create a document. If `sequence` is missing, assign the next free one for (kind, year).
        Rows of the series are locked and the insert is retried on collision, so two
        simultaneous creates can't end up with the same number.
        """
        auto_sequence = fields.get('sequence') is None
        for attempt in range(attempts):
            try:
                with transaction.atomic():
                    if auto_sequence:
                        fields['sequence'] = cls.next_sequence(fields['kind'], fields['year'], lock=True)
                    return cls.objects.create(**fields)
            except IntegrityError:
                if not auto_sequence or attempt == attempts - 1:
                    raise
