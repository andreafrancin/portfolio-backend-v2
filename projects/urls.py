from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import ProjectViewSet, ProjectImageUploadView

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')

urlpatterns = router.urls

urlpatterns += [
    path('projects/<int:project_id>/upload_image/', ProjectImageUploadView.as_view(), name='project-upload-image'),
]
