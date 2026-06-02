from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action

from .permissions import IsAdmin, IsManager, IsEmployee
from auth_app.models import User
from .serializers import UserSerializer, MeUpdateSerializer, MeSerializer


class UserViewSet(
    mixins.ListModelMixin,  # GET
    mixins.RetrieveModelMixin,  # GET id
    mixins.UpdateModelMixin,  # PUT, PATCH
    mixins.DestroyModelMixin,  # DELETE
    viewsets.GenericViewSet,
):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsManager]

    @action(
        detail=False,
        methods=['get', 'patch'],
        permission_classes=[IsEmployee]
    )
    def me(self, request):
        if request.method == 'GET':
            serializer = MeSerializer(request.user)
            return Response(serializer.data)

        serializer = MeUpdateSerializer(
            request.user,
            data=request.data,
            partial=True  # щоб оновлювати лише частину полів
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)
