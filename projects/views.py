from django.db import transaction, models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import Project
from .serializers import ProjectSerializer
from .services.aws_s3 import handle_image_upload


class ProjectViewSet(viewsets.ModelViewSet):
    """
    Endpoints:
    - GET    /projects/            → List all projects
    - GET    /projects/{id}/       → Get a project
    - POST   /projects/            → Create a project
    - PUT    /projects/{id}/       → Modify a project
    - DELETE /projects/{id}/       → Remove a project
    - POST   /projects/reorder/    → Change projects order
    """
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        max_order = Project.objects.aggregate(models.Max('order'))['order__max']
        next_order = (max_order + 1) if max_order is not None else 0
        serializer.save(order=next_order)

    @action(detail=False, methods=['post'])
    def reorder(self, request):
        order_list = request.data.get('order')
        if not isinstance(order_list, list):
            return Response(
                {"error": "Field 'order' must be a list of IDs"},
                status=status.HTTP_400_BAD_REQUEST
            )

        projects = list(Project.objects.filter(id__in=order_list))
        if set(order_list) != {p.id for p in projects}:
            return Response(
                {"error": "The list of IDs does not match with existing projects"},
                status=status.HTTP_400_BAD_REQUEST
            )

        id_to_project = {p.id: p for p in projects}
        updated = []
        for idx, pid in enumerate(order_list):
            project = id_to_project[pid]
            project.order = idx
            updated.append(project)

        with transaction.atomic():
            Project.objects.bulk_update(updated, ['order'])

        return Response({"status": "Order updated."})


class ProjectImageUploadView(APIView):
    """
    Endpoint:
    - POST /projects/{project_id}/upload_image/
      → Upload a new image and remove the existing ones if specified.
    """
    def post(self, request, project_id):
        file_obj = request.FILES.get('image')
        existing_images = request.data.get('existingImages', [])

        if not file_obj:
            return Response({'error': 'No se ha enviado ninguna imagen.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_image_key = handle_image_upload(project_id, file_obj, existing_images)
            return Response({'new_image': new_image_key}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
