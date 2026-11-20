from django.db import models


class DailySalt(models.Model):
    """The secret mixed into visitor codes for one day. Deleting it makes that day's codes unlinkable."""
    day = models.DateField(unique=True)
    salt = models.CharField(max_length=64)


class PageView(models.Model):
    """One public page shown to one visitor. No IP address or identifier that outlives the day is stored."""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    day = models.DateField(db_index=True)
    visitor = models.CharField(max_length=24, db_index=True)
    session = models.CharField(max_length=24, db_index=True)
    path = models.CharField(max_length=255)
    page = models.CharField(max_length=20, db_index=True)
    project_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    is_entry = models.BooleanField(default=False)
    source = models.CharField(max_length=60, blank=True)
    referrer_host = models.CharField(max_length=120, blank=True)
    campaign = models.CharField(max_length=80, blank=True)
    country = models.CharField(max_length=2, blank=True)
    language = models.CharField(max_length=5, blank=True)
    device = models.CharField(max_length=10, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    scroll_pct = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["day", "page"])]


class Event(models.Model):
    """Something done on a page: opening the contact form, clicking Instagram, opening an image..."""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    day = models.DateField(db_index=True)
    visitor = models.CharField(max_length=24, db_index=True)
    session = models.CharField(max_length=24)
    name = models.CharField(max_length=40, db_index=True)
    value = models.CharField(max_length=160, blank=True)
    path = models.CharField(max_length=255, blank=True)
    project_id = models.PositiveIntegerField(null=True, blank=True)


class AnalyticsSettings(models.Model):
    """Which sections the statistics page shows. One record for the whole back office."""
    hidden_sections = models.JSONField(default=list, blank=True)

    @classmethod
    def load(cls) -> "AnalyticsSettings":
        return cls.objects.order_by("id").first() or cls.objects.create()
