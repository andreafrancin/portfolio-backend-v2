# siteinfo/serializers.py
from rest_framework import serializers
from .models import About, Contact

class AboutSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = About
        fields = ['id', 'image', 'image_url', 'title_i18n', 'content_i18n']
        extra_kwargs = {
            'image': {'write_only': True, 'required': False}
        }

    def get_image_url(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None

    def update(self, instance, validated_data):
        # Merge i18n fields instead of replacing whole dict
        for field in ['title_i18n', 'content_i18n']:
            if field in validated_data:
                current = getattr(instance, field, {}) or {}
                current.update(validated_data[field])
                setattr(instance, field, current)

        if 'image' in validated_data:
            instance.image = validated_data['image']

        instance.save()
        return instance


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
