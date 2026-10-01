from django.contrib import admin
from .models import IssuerProfile, Client, Condition, Document


@admin.register(IssuerProfile)
class IssuerProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'legal_name', 'tax_id', 'city', 'updated_at')


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'tax_id', 'email', 'updated_at')
    search_fields = ('name', 'tax_id')


@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'updated_at')
    search_fields = ('title', 'text')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'kind', 'number', 'date', 'status', 'client_name', 'total_amount')
    list_filter = ('kind', 'year', 'status')

    def client_name(self, obj):
        return (obj.client_snapshot or {}).get('name') or '-'
