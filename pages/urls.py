# siteinfo/urls.py
from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import (
    AboutViewSet,
    AutoReplyPreviewView,
    AutoReplyTestView,
    AutoReplyView,
    ContactMessageView,
    ContactViewSet,
    ServiceGroupViewSet,
    ServiceViewSet,
)

router = DefaultRouter()
router.register(r'about', AboutViewSet, basename='about')
router.register(r'contact', ContactViewSet, basename='contact')
router.register(r'service-groups', ServiceGroupViewSet, basename='service-group')
router.register(r'services', ServiceViewSet, basename='service')

urlpatterns = router.urls
urlpatterns += [
    path('contact-messages/', ContactMessageView.as_view(), name='contact-message'),
    path('auto-reply/', AutoReplyView.as_view(), name='auto-reply'),
    path('auto-reply/preview/', AutoReplyPreviewView.as_view(), name='auto-reply-preview'),
    path('auto-reply/test/', AutoReplyTestView.as_view(), name='auto-reply-test'),
]
