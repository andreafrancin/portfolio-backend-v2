# pages/models.py
import os
import uuid
import hashlib
from io import BytesIO
from django.db import models
from django.utils.text import slugify
from django.core.files.base import ContentFile
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from storages.backends.s3boto3 import S3Boto3Storage
from PIL import Image, ImageFilter


def about_image_upload_to(instance, filename):
    """
    Generates a unique and readable key for each uploaded image.
    Format: about/<uuid>_<slug>.<ext>
    """
    base, ext = os.path.splitext(filename)
    return f"about/{uuid.uuid4().hex}_{slugify(base)}{ext.lower()}"


def about_image_low_upload_to(instance, filename):
    base, _ = os.path.splitext(filename)
    return f"about/low/{uuid.uuid4().hex}_{slugify(base)}.webp"


class About(models.Model):
    # Legacy field kept for backward compatibility
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
        for img in self.images.all():
            img.delete()
        super().delete(*args, **kwargs)


class AboutImage(models.Model):
    about = models.ForeignKey(About, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(storage=S3Boto3Storage(), upload_to=about_image_upload_to)
    image_low = models.ImageField(
        storage=S3Boto3Storage(),
        upload_to=about_image_low_upload_to,
        blank=True,
        null=True,
        editable=False,
    )
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_cover = models.BooleanField(default=False)
    hash = models.CharField(max_length=64, blank=True, editable=False)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"About image - {self.caption or self.id}"

    def _generate_low_variant(self):
        if not self.image:
            return

        self.image.open()
        try:
            self.image.seek(0)
        except Exception:
            pass
        im = Image.open(self.image)
        im.load()

        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")

        target_width = 240
        if im.width > target_width:
            ratio = target_width / float(im.width)
            new_size = (target_width, max(1, int(im.height * ratio)))
            im = im.resize(new_size, Image.LANCZOS)

        im = im.filter(ImageFilter.GaussianBlur(radius=12))

        buf = BytesIO()
        im.save(buf, format="WEBP", quality=40, method=6)
        buf.seek(0)

        base, _ = os.path.splitext(os.path.basename(self.image.name))
        low_name = f"{base}.webp"
        self.image_low.save(low_name, ContentFile(buf.read()), save=False)

    def save(self, *args, **kwargs):
        if self.image and not self.hash:
            if hasattr(self.image, "file") and hasattr(self.image.file, "read"):
                pos = None
                try:
                    pos = self.image.file.tell()
                except Exception:
                    pass
                try:
                    self.image.seek(0)
                    data = self.image.read()
                    if data:
                        self.hash = hashlib.sha256(data).hexdigest()
                finally:
                    try:
                        self.image.seek(pos or 0)
                    except Exception:
                        pass

        regenerate_low = False
        old_image_name = None
        if self.pk:
            try:
                old = AboutImage.objects.only("image", "image_low").get(pk=self.pk)
                old_image_name = old.image.name if old.image else None
            except AboutImage.DoesNotExist:
                pass

        new_image_name = self.image.name if self.image else None

        if not self.pk:
            regenerate_low = True
        elif (old_image_name != new_image_name) and new_image_name:
            regenerate_low = True
        elif not self.image_low and new_image_name:
            regenerate_low = True

        super().save(*args, **kwargs)

        if regenerate_low and self.image:
            try:
                self._generate_low_variant()
                super().save(update_fields=["image_low"])
            except Exception:
                pass

    def delete(self, *args, **kwargs):
        file_name = self.image.name
        storage = self.image.storage if self.image else None

        low_file_name = self.image_low.name if self.image_low else None
        low_storage = self.image_low.storage if self.image_low else None

        super().delete(*args, **kwargs)

        if storage and file_name:
            storage.delete(file_name)
        if low_storage and low_file_name:
            low_storage.delete(low_file_name)


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
