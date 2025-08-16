from adminsortable2.admin import SortableInlineAdminMixin, SortableAdminMixin
from django.contrib import admin
from .models import Project, ProjectImage

class ProjectImageInline(SortableInlineAdminMixin, admin.TabularInline):
    model = ProjectImage
    extra = 1
    fields = ('image', 'caption', 'order')
    readonly_fields = ()

@admin.register(Project)
class ProjectAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'title', 'order', 'short_content', 'content_source_lang')
    ordering = ('order',)
    inlines = [ProjectImageInline]

    def short_content(self, obj):
        txt = obj.content or ""
        return (txt[:50] + "...") if len(txt) > 50 else (txt or "-")
    short_content.short_description = "Content (Markdown base)"
