from rest_framework import mixins, permissions, viewsets

from mesads.app.models import ADSUpdateFile

from .serializers import ADSUpdateFileSerializer


class ADSUpdatesViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = ADSUpdateFileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ADSUpdateFile.objects.filter(user=self.request.user).order_by('-creation_date')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
