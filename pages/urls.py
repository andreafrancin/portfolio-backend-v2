# siteinfo/urls.py
from rest_framework.routers import DefaultRouter
from .views import AboutViewSet, ContactViewSet

router = DefaultRouter()
router.register(r'about', AboutViewSet, basename='about')
router.register(r'contact', ContactViewSet, basename='contact')

urlpatterns = router.urls
