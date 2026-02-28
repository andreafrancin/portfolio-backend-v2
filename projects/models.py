from django.db import models
from storages.backends.s3boto3 import S3Boto3Storage
from django.utils.text import slugify
import hashlib
import os
import uuid

from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image, ImageFilter


class Project(models.Model):
    title = models.CharField(max_length=255)

    content = models.TextField(blank=True, null=True)
    content_source_lang = models.CharField(max_length=8, default="es")
    title_i18n = models.JSONField(default=dict, blank=True)
    content_i18n = models.JSONField(default=dict, blank=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

    def delete(self, *args, **kwargs):
        """
        Override delete to ensure related images are removed from S3 before deleting project.
        """
        for img in self.images.all():
            img.delete()
        super().delete(*args, **kwargs)


def project_image_upload_to(instance, filename):
    base, ext = os.path.splitext(filename)
    return f"projects/{uuid.uuid4().hex}_{slugify(base)}{ext.lower()}"


def project_image_low_upload_to(instance, filename):
    base, _ = os.path.splitext(filename)
    return f"projects/low/{uuid.uuid4().hex}_{slugify(base)}.webp"


class ProjectImage(models.Model):
    project = models.ForeignKey(Project, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(storage=S3Boto3Storage(), upload_to=project_image_upload_to)
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_cover = models.BooleanField(default=False)
    hash = models.CharField(max_length=64, blank=True, editable=False)

    image_low = models.ImageField(
        storage=S3Boto3Storage(),
        upload_to=project_image_low_upload_to,
        blank=True,
        null=True,
        editable=False,
    )

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.project.title} - {self.caption or self.id}"

    def _generate_low_variant(self):
        if not self.image:
            return

        # Open original
        self.image.open()
        try:
            self.image.seek(0)
        except Exception:
            pass
        im = Image.open(self.image)
        im.load()

        # Convert to RGB if necessary (for WEBP with solid background)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")

        # Downscale to very small size (LQIP)
        target_width = 240
        if im.width > target_width:
            ratio = target_width / float(im.width)
            new_size = (target_width, max(1, int(im.height * ratio)))
            im = im.resize(new_size, Image.LANCZOS)

        # Apply strong blur
        im = im.filter(ImageFilter.GaussianBlur(radius=12))

        # Save as heavily compressed WEBP
        buf = BytesIO()
        im.save(buf, format="WEBP", quality=40, method=6)
        buf.seek(0)

        # Derived name
        base, _ = os.path.splitext(os.path.basename(self.image.name))
        low_name = f"{base}.webp"  # upload_to will add 'projects/low/'

        # Save to the configured storage for the field
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

        # Check whether we need to regenerate low-res (conservative)
        regenerate_low = False
        old_image_name = None
        if self.pk:
            try:
                old = ProjectImage.objects.only("image", "image_low").get(pk=self.pk)
                old_image_name = old.image.name if old.image else None
            except ProjectImage.DoesNotExist:
                pass

        new_image_name = self.image.name if self.image else None

        if not self.pk:
            # New record
            regenerate_low = True
        elif (old_image_name != new_image_name) and new_image_name:
            # Main image has changed
            regenerate_low = True
        elif not self.image_low and new_image_name:
            # No low-res yet
            regenerate_low = True

        # Main save
        super().save(*args, **kwargs)

        # Low-res generation only when needed
        if regenerate_low and self.image:
            try:
                self._generate_low_variant()
                super().save(update_fields=["image_low"])
            except Exception:
                # Do not block if low-res generation fails
                pass

    def delete(self, *args, **kwargs):
        """
        Deletes the DB record and then removes the file from S3.
        """
        file_name = self.image.name
        storage = self.image.storage if self.image else None

        # Also clean up the linked low-res file
        low_file_name = self.image_low.name if self.image_low else None
        low_storage = self.image_low.storage if self.image_low else None

        super().delete(*args, **kwargs)

        if storage and file_name:
            storage.delete(file_name)
        if low_storage and low_file_name:
            low_storage.delete(low_file_name)
