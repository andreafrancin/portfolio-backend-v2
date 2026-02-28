from rest_framework import serializers
from django.core.files.base import ContentFile
from .models import Project, ProjectImage
import hashlib
import base64
import uuid


class ProjectImageSerializer(serializers.ModelSerializer):
    # Explicit id so DRF doesn't make it read-only (needed for nested update by id)
    id = serializers.IntegerField(required=False)
    # write-only: accepts base64 when creating/updating the main image
    image = serializers.CharField(required=False, write_only=True)
    # read-only: public URL for the main image
    image_url = serializers.SerializerMethodField(read_only=True)
    # read-only: public URL for the blurred low-res placeholder
    image_low_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ProjectImage
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


class ProjectSerializer(serializers.ModelSerializer):
    images = ProjectImageSerializer(many=True)
    images_to_remove = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True,
    )

    title_i18n = serializers.JSONField(required=False)
    content_i18n = serializers.JSONField(required=False)
    content_source_lang = serializers.CharField(required=False)

    title_resolved = serializers.SerializerMethodField(read_only=True)
    content_resolved = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Project
        fields = [
            'id',
            'title', 'content', 'content_source_lang',
            'title_i18n', 'content_i18n',
            'title_resolved', 'content_resolved',
            'order',
            'hidden',
            'images', 'images_to_remove',
        ]
        read_only_fields = ['id', 'order', 'title_resolved', 'content_resolved']

    # ---------- language helpers ----------
    def _resolve_lang(self):
        request = self.context.get('request')
        return (request.query_params.get('lang') if request else None) or None

    def get_title_resolved(self, obj):
        lang = self._resolve_lang()
        if lang and isinstance(obj.title_i18n, dict) and obj.title_i18n.get(lang):
            return {'text': obj.title_i18n[lang], 'lang': lang}
        if lang == obj.content_source_lang:
            return {'text': obj.title, 'lang': obj.content_source_lang}
        if obj.title:
            return {'text': obj.title, 'lang': obj.content_source_lang}
        if isinstance(obj.title_i18n, dict) and obj.title_i18n:
            k, v = next(iter(obj.title_i18n.items()))
            return {'text': v, 'lang': k}
        return {'text': None, 'lang': None}

    def get_content_resolved(self, obj):
        lang = self._resolve_lang()
        if lang and isinstance(obj.content_i18n, dict):
            d = obj.content_i18n.get(lang)
            if isinstance(d, dict) and d.get('md'):
                return {'md': d['md'], 'lang': lang}
        if lang == obj.content_source_lang and obj.content is not None:
            return {'md': obj.content, 'lang': obj.content_source_lang}
        if obj.content is not None:
            return {'md': obj.content, 'lang': obj.content_source_lang}
        if isinstance(obj.content_i18n, dict) and obj.content_i18n:
            k, v = next(iter(obj.content_i18n.items()))
            if isinstance(v, dict) and v.get('md'):
                return {'md': v['md'], 'lang': k}
        return {'md': None, 'lang': None}

    # ---------- helpers ----------
    def _merge_dicts(self, original: dict, incoming: dict) -> dict:
        if not isinstance(original, dict):
            original = {}
        if not isinstance(incoming, dict):
            return original
        merged = original.copy()
        merged.update(incoming)
        return merged

    def _enforce_single_cover(self, project):
        """Ensure at most one image per project has is_cover=True."""
        cover_images = project.images.filter(is_cover=True)
        if cover_images.count() > 1:
            # Keep only the first one as cover
            first = cover_images.first()
            cover_images.exclude(pk=first.pk).update(is_cover=False)

    # ---------- create / update ----------
    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        title_i18n_in = validated_data.pop('title_i18n', {})
        content_i18n_in = validated_data.pop('content_i18n', {})

        project = Project.objects.create(
            title=validated_data.get('title', ''),
            content=validated_data.get('content', None),
            content_source_lang=validated_data.get('content_source_lang', 'en'),
            order=validated_data.get('order', 0),
            hidden=validated_data.get('hidden', False),
            title_i18n=self._merge_dicts({}, title_i18n_in),
            content_i18n=self._merge_dicts({}, content_i18n_in),
        )

        for img in images_data:
            img_base64 = img.get('image')
            if not img_base64:
                continue
            file_obj, hash_val = ProjectImageSerializer()._get_image_file_and_hash(img_base64)
            if not file_obj:
                continue
            ProjectImage.objects.create(
                project=project,
                image=file_obj,
                hash=hash_val,
                caption=img.get('caption', ''),
                order=img.get('order', 0),
                is_cover=img.get('is_cover', False),
            )

        self._enforce_single_cover(project)
        return project

    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', [])
        ids_to_remove = validated_data.pop('images_to_remove', [])

        if 'title' in validated_data:
            instance.title = validated_data['title']
        if 'content' in validated_data:
            instance.content = validated_data['content']
        if 'content_source_lang' in validated_data:
            instance.content_source_lang = validated_data['content_source_lang']
        if 'hidden' in validated_data:
            instance.hidden = validated_data['hidden']

        if 'title_i18n' in validated_data:
            instance.title_i18n = self._merge_dicts(instance.title_i18n, validated_data['title_i18n'])
        if 'content_i18n' in validated_data:
            instance.content_i18n = self._merge_dicts(instance.content_i18n, validated_data['content_i18n'])

        instance.save()

        # 1) explicit deletions
        if ids_to_remove:
            qs = instance.images.filter(id__in=ids_to_remove)
            for img in qs:
                img.delete()

        # 2) First pass: clear is_cover on all existing images if any incoming image claims cover
        any_incoming_cover = any(img_data.get('is_cover', False) for img_data in images_data)
        if any_incoming_cover:
            instance.images.filter(is_cover=True).update(is_cover=False)

        # 3) updates and creations
        for img_data in images_data:
            img_id = img_data.get('id')

            if img_id:
                try:
                    img = instance.images.get(id=img_id)
                except ProjectImage.DoesNotExist:
                    continue
                ProjectImageSerializer(context=self.context).update(img, img_data)
            else:
                img_base64 = img_data.get('image')
                if not img_base64:
                    continue
                file_obj, hash_val = ProjectImageSerializer()._get_image_file_and_hash(img_base64)
                if not file_obj:
                    continue
                ProjectImage.objects.create(
                    project=instance,
                    image=file_obj,
                    hash=hash_val,
                    caption=img_data.get('caption', ''),
                    order=img_data.get('order', 0),
                    is_cover=img_data.get('is_cover', False),
                )

        self._enforce_single_cover(instance)
        return instance
