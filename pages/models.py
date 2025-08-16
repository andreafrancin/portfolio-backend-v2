# pages/models.py
import os
import uuid
import hashlib
from django.db import models
from django.utils.text import slugify
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from storages.backends.s3boto3 import S3Boto3Storage


def about_image_upload_to(instance, filename):
    """
    Generates a unique and readable key for each uploaded image.
    Format: about/<uuid>_<slug>.<ext>
    """
    base, ext = os.path.splitext(filename)
    return f"about/{uuid.uuid4().hex}_{slugify(base)}{ext.lower()}"


class About(models.Model):
    image = models.ImageField(
        storage=S3Boto3Storage(),
        upload_to=about_image_upload_to,
        blank=True,
        null=True
    )
    title_i18n = models.JSONField(default=dict, blank=True)
    content_i18n = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "About"
        verbose_name_plural = "About"

    def __str__(self):
        return "About section"

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)


class Contact(models.Model):
    title_i18n = models.JSONField(default=dict, blank=True)
    description_i18n = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Contact"
        verbose_name_plural = "Contact"

    def __str__(self):
        return "Contact section"


@receiver(pre_save, sender=About)
def delete_old_about_image_on_change(sender, instance: About, **kwargs):
    """
    If the About.image is being replaced or cleared in admin, delete the old file from S3.
    - Covers both: changing the file and clearing it with the "clear" checkbox.
    """
    if not instance.pk:
        return  # new object; nothing to clean

    try:
        old = About.objects.get(pk=instance.pk)
    except About.DoesNotExist:
        return

    old_file = getattr(old, "image", None)
    new_file = getattr(instance, "image", None)

    # If there was an old file and it's different from the new one (or cleared), delete old from S3
    if old_file and old_file.name and old_file != new_file:
        try:
            old_file.delete(save=False)  # remove from S3
        except Exception:
            pass


@receiver(post_delete, sender=About)
def delete_about_image_on_delete(sender, instance: About, **kwargs):
    """
    When the About record is deleted, remove its file from S3.
    (In case it wasn't already removed by pre_save or custom delete)
    """
    file = getattr(instance, "image", None)
    if file:
        try:
            file.delete(save=False)
        except Exception:
            pass
