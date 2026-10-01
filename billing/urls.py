from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import IssuerProfileView, ClientViewSet, ConditionViewSet, DocumentViewSet

router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='billing-client')
router.register(r'conditions', ConditionViewSet, basename='billing-condition')
router.register(r'documents', DocumentViewSet, basename='billing-document')

urlpatterns = [
    path('issuer/', IssuerProfileView.as_view(), name='billing-issuer'),
]

urlpatterns += router.urls
