# pages/serializers.py
from rest_framework import serializers
from django.core.files.base import ContentFile
from .models import About, AboutImage, Contact
import hashlib
import base64
import uuid


class AboutImageSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    image = serializers.CharField(required=False, write_only=True)
    image_url = serializers.SerializerMethodField(read_only=True)
    image_low_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AboutImage
        fields = ['id', 'image', 'image_url', 'image_low_url', 'caption', 'order', 'is_cover', 'hash']

    def get_image_url(self, obj):
        try:
            if obj.image and hasattr(obj.image, 'url'):
                request = self.context.get('request')
                url = obj.image.url
                return request.build_absolute_uri(url) if request else url
        except Exception:
            pass
        return None

    def get_image_low_url(self, obj):
        try:
            if obj.image_low and hasattr(obj.image_low, 'url'):
                request = self.context.get('request')
                url = obj.image_low.url
                return request.build_absolute_uri(url) if request else url
        except Exception:
            pass
        return None

    def _get_image_file_and_hash(self, base64_string):
        if isinstance(base64_string, str) and base64_string.startswith('data:image'):
            try:
                fmt, b64 = base64_string.split(';base64,')
                ext = fmt.split('/')[-1]
                data = base64.b64decode(b64)
            except Exception:
                return None, None
            filename = f"{uuid.uuid4().hex}.{ext}"
            content_file = ContentFile(data, name=filename)
            hash_val = hashlib.sha256(data).hexdigest()
            return content_file, hash_val
        return None, None

    def create(self, validated_data):
        img_data = validated_data.pop('image', None)
        if img_data:
            file_obj, hash_val = self._get_image_file_and_hash(img_data)
            if file_obj is None:
                raise serializers.ValidationError("Invalid image payload for new image.")
            validated_data['image'] = file_obj
            validated_data['hash'] = hash_val
        else:
            raise serializers.ValidationError("New images must include a base64 'image'.")
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'caption' in validated_data:
            instance.caption = validated_data['caption']
        if 'order' in validated_data:
            instance.order = validated_data['order']
        if 'is_cover' in validated_data:
            instance.is_cover = validated_data['is_cover']

        img_data = validated_data.get('image')
        if img_data:
            file_obj, hash_val = self._get_image_file_and_hash(img_data)
            if file_obj:
                instance.image = file_obj
                instance.hash = hash_val

        instance.save()
        return instance


class AboutSerializer(serializers.ModelSerializer):
    # Legacy field
    image_url = serializers.SerializerMethodField(read_only=True)
    # New nested images
    images = AboutImageSerializer(many=True, required=False)
    images_to_remove = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True,
    )

    class Meta:
        model = About
        fields = ['id', 'image', 'image_url', 'images', 'images_to_remove', 'title_i18n', 'content_i18n']
        extra_kwargs = {
            'image': {'write_only': True, 'required': False}
        }

    def get_image_url(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None

    def _enforce_single_cover(self, about):
        cover_images = about.images.filter(is_cover=True)
        if cover_images.count() > 1:
            first = cover_images.first()
            cover_images.exclude(pk=first.pk).update(is_cover=False)

    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', [])
        ids_to_remove = validated_data.pop('images_to_remove', [])

        # Merge i18n fields instead of replacing whole dict
        for field in ['title_i18n', 'content_i18n']:
            if field in validated_data:
                current = getattr(instance, field, {}) or {}
                current.update(validated_data[field])
                setattr(instance, field, current)

        if 'image' in validated_data:
            instance.image = validated_data['image']

        instance.save()

        # 1) explicit deletions
        if ids_to_remove:
            qs = instance.images.filter(id__in=ids_to_remove)
            for img in qs:
                img.delete()

        # 2) Clear is_cover on all existing images if any incoming image claims cover
        any_incoming_cover = any(img_data.get('is_cover', False) for img_data in images_data)
        if any_incoming_cover:
            instance.images.filter(is_cover=True).update(is_cover=False)

        # 3) updates and creations
        for img_data in images_data:
            img_id = img_data.get('id')

            if img_id:
                try:
                    img = instance.images.get(id=img_id)
                except AboutImage.DoesNotExist:
                    continue
                AboutImageSerializer(context=self.context).update(img, img_data)
            else:
                img_base64 = img_data.get('image')
                if not img_base64:
                    continue
                file_obj, hash_val = AboutImageSerializer()._get_image_file_and_hash(img_base64)
                if not file_obj:
                    continue
                AboutImage.objects.create(
                    about=instance,
                    image=file_obj,
                    hash=hash_val,
                    caption=img_data.get('caption', ''),
                    order=img_data.get('order', 0),
                    is_cover=img_data.get('is_cover', False),
                )

        self._enforce_single_cover(instance)
        return instance

    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        validated_data.pop('images_to_remove', [])

        about = About.objects.create(
            title_i18n=validated_data.get('title_i18n', {}),
            content_i18n=validated_data.get('content_i18n', {}),
        )

        if 'image' in validated_data:
            about.image = validated_data['image']
            about.save()

        for img in images_data:
            img_base64 = img.get('image')
            if not img_base64:
                continue
            file_obj, hash_val = AboutImageSerializer()._get_image_file_and_hash(img_base64)
            if not file_obj:
                continue
            AboutImage.objects.create(
                about=about,
                image=file_obj,
                hash=hash_val,
                caption=img.get('caption', ''),
                order=img.get('order', 0),
                is_cover=img.get('is_cover', False),
            )

        self._enforce_single_cover(about)
        return about


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'title_i18n', 'description_i18n']

    def update(self, instance, validated_data):
        for field in ['title_i18n', 'description_i18n']:
            if field in validated_data:
                current = getattr(instance, field, {}) or {}
                current.update(validated_data[field])
                setattr(instance, field, current)

        instance.save()
        return instance
