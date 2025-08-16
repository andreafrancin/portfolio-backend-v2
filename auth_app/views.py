from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

class IsAndrea(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.username == "andreafrancin")

class PrivateAreaView(APIView):
    permission_classes = [IsAndrea]

    def get(self, request):
        return Response(
            {"message": "Welcome Andrea Francin, this is your private area."},
            status=status.HTTP_200_OK
        )
