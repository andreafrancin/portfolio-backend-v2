from django.contrib import admin
from django.utils.html import format_html
from .models import About, AboutImage, Contact


class AboutImageInline(admin.TabularInline):
    model = AboutImage
    extra = 0
    fields = ("image", "caption", "order", "is_cover")
    readonly_fields = ()


@admin.register(About)
class AboutAdmin(admin.ModelAdmin):
    list_display = ("id", "image_preview", "langs_title", "langs_content", "updated_at")
    readonly_fields = ("image_preview",)
    inlines = [AboutImageInline]

    def image_preview(self, obj):
        try:
            if obj.image and hasattr(obj.image, "url"):
                return format_html('<img src="{}" style="max-height:80px;" />', obj.image.url)
        except Exception:
            pass
        return "-"
    image_preview.short_description = "Image"

    def langs_title(self, obj):
        return ", ".join(sorted(obj.title_i18n.keys())) if obj.title_i18n else "-"
    langs_title.short_description = "Title langs"

    def langs_content(self, obj):
        return ", ".join(sorted(obj.content_i18n.keys())) if obj.content_i18n else "-"
    langs_content.short_description = "Content langs"

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("id", "langs_title", "langs_desc", "updated_at")

    def langs_title(self, obj):
        return ", ".join(sorted(obj.title_i18n.keys())) if obj.title_i18n else "-"
    langs_title.short_description = "Title langs"

    def langs_desc(self, obj):
        return ", ".join(sorted(obj.description_i18n.keys())) if obj.description_i18n else "-"
    langs_desc.short_description = "Description langs"
