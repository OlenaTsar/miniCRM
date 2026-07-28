from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser

from CRM.permissions import IsAdmin, IsManager, IsEmployee
from auth_app.models import User, UserRole, Team
from crm_app.models import Product, Pipeline
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
        elif user.role == UserRole.MANAGER:
            return User.objects.filter(team=user.team)
        else:
            return User.objects.none()

    @action(detail=False, methods=['get', 'patch'], permission_classes=[IsEmployee])
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
        elif user.role == UserRole.MANAGER:
            return Team.objects.filter(id=user.team.id)
        else:
            return Team.objects.none()

    @action(detail=True, methods=["post"], url_path="add-user")
    def add_user(self, request, pk=None):
        team = self.get_object()
        user_id = request.data.get("user")
        user_obj = get_object_or_404(User, id=user_id)

        if user_obj.team == team:
            return Response({"detail": "Користувач вже є в цій команді."}, status=400)

        if user_obj.team is not None:
            return Response({"detail": f"Користувач вже є в команді {user_obj.team.name}. "
                                       f"Спочатку видаліть користувача з неї"}, status=400)

        user_obj.team = team
        user_obj.save()
        return Response({"detail": "Користувача додано."})

    @action(detail=True, methods=["post"], url_path="remove-user")
    def remove_user(self, request, pk=None):
        team = self.get_object()
        user_id = request.data.get("user")
        user_obj = get_object_or_404(User, id=user_id)

        if user_obj.team != team:
            return Response({"detail": "Користувача немає в цій команді."}, status=400)

        user_obj.team = None
        user_obj.save()
        return Response({"detail": "Користувача видалено."})

    @action(detail=True, methods=["post"], url_path="add-product")
    def add_product(self, request, pk=None):
        team = self.get_object()
        product_id = request.data.get("product")

        if team.products.filter(id=product_id).exists():
            return Response({"detail": "Команда вже працює з цим продуктом."}, status=400)

        product = get_object_or_404(Product, id=product_id)
        team.products.add(product)

        # створення pipeline для кожного користувача
        for user in team.users.all():
            Pipeline.objects.create(
                name=product.name,
                product=product,
                assigned_to=user,
            )

        return Response({"detail": f"{product.name} додано."})

    @action(detail=True, methods=["post"], url_path="remove-product")
    def remove_product(self, request, pk=None):
        team = self.get_object()
        product_id = request.data.get("product")

        if not team.products.filter(id=product_id).exists():
            return Response({"detail": "Команда не працює з цим продуктом."}, status=400)

        product = get_object_or_404(Product, id=product_id)
        team.products.remove(product)

        # видалення pipeline, пов'язаних з цим product, у кожного користувача
        # for pipeline in product.pipelines.all().filter(assigned_to__team=team):
        #     pipeline.delete()

        return Response({"detail": f"{product.name} видалено."})
