from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser

from .permissions import IsAdmin, IsManager, IsEmployee
from auth_app.models import User, UserRole, Team
from crm_app.models import Product
from .serializers import UserSerializer, MeUpdateSerializer, MeSerializer, TeamSerializer


class UserViewSet(
    mixins.ListModelMixin,  # GET
    mixins.RetrieveModelMixin,  # GET id
    mixins.UpdateModelMixin,  # PUT, PATCH
    mixins.DestroyModelMixin,  # DELETE
    viewsets.GenericViewSet,
):
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == "me":
            return [IsEmployee()]
        if self.action in ["list",  # GET
                           "retrieve",  # GET id
                           "partial_update",  # PATCH
                           ]:
            return [IsManager()]
        return [IsAdmin()]

    def get_queryset(self):

        user = self.request.user

        if user.role == UserRole.ADMIN:
            return User.objects.all()

        return User.objects.filter(team=user.team)

    @action(
        detail=False,
        methods=['get', 'patch'],
        permission_classes=[IsEmployee]
    )
    def me(self, request):
        if request.method == 'GET':
            serializer = MeSerializer(request.user)
            return Response(serializer.data)

        # PATCH
        self.parser_classes = [MultiPartParser, FormParser]  # для avatar

        serializer = MeUpdateSerializer(
            request.user,
            data=request.data,
            partial=True  # щоб оновлювати лише частину полів
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)


class TeamViewSet(ModelViewSet):
    serializer_class = TeamSerializer

    def get_permissions(self):
        if self.action in [
            "list",  # GET
            "retrieve",  # GET id
            "partial_update",  # PATCH
            "remove_user",
            "add_product",
            "remove_product",
        ]:
            return [IsManager()]
        return [IsAdmin()]

    def get_queryset(self):

        user = self.request.user

        if user.role == UserRole.ADMIN:
            return Team.objects.all()
        else:
            return Team.objects.filter(users__team=user.team, users__role=UserRole.MANAGER)

    @action(detail=True, methods=["post"], url_path="add-user")
    def add_user(self, request, pk=None):
        team = self.get_object()
        user_id = request.data.get("user")
        user_obj = get_object_or_404(User, id=user_id)

        if user_obj.team == team:
            return Response({"detail": "Користувач вже є в цій команді."})

        if user_obj.team is not None:
            return Response({"detail": f"Користувач вже є в команді {team.name}. Спочатку видаліть користувача з неї"})

        user_obj.team = team
        user_obj.save()
        return Response({"detail": "Користувача додано."})

    @action(detail=True, methods=["post"], url_path="remove-user")
    def remove_user(self, request, pk=None):
        team = self.get_object()
        user_id = request.data.get("user")
        user_obj = get_object_or_404(User, id=user_id)

        if user_obj.team != team:
            return Response({"detail": "Користувача немає в цій команді."})

        user_obj.team = None
        user_obj.save()
        return Response({"detail": "Користувача видалено."})

    @action(detail=True, methods=["post"], url_path="add-product")
    def add_product(self, request, pk=None):
        team = self.get_object()
        product_name = request.data.get("product")

        # if team.products.filter(name=product_name).exists():
        #     return Response({"detail": "Команда вже працює з цим продуктом."})

        # product name є унікальним, тому шукаємо за ним, а не за id
        product = get_object_or_404(Product, name=product_name)
        team.products.add(product)

        return Response({"detail": f"{product_name} додано."})

    @action(detail=True, methods=["post"], url_path="remove-product")
    def remove_product(self, request, pk=None):
        team = self.get_object()
        product_name = request.data.get("product")
        product = get_object_or_404(Product, name=product_name)

        team.products.remove(product)

        return Response({"detail": "Користувача видалено."})
