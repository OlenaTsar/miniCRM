from django.http import HttpResponse
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import MultiPartParser
from tablib import Dataset

from .permissions import IsSalesRep, IsManager
from auth_app.models import UserRole
from .models import Company, Contact, Product, Deal, Pipeline, PipelineStage, DealStatus
from .serializers import (
    CompanySerializer,
    ContactSerializer,
    ProductSerializer,
    PipelineSerializer,
    DealSerializer,
    ChangeStageSerializer,
    DealStageHistorySerializer,
)
from .filters import ContactFilter, CompanyFilter, DealFilter
from .resources import ContactResource


class CompanyViewSet(ModelViewSet):
    serializer_class = CompanySerializer
    permission_classes = [IsSalesRep]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CompanyFilter
    search_fields = [
        "name",
        "industry",
        "email",
        "website",
    ]
    ordering_fields = [
        "name",
        "industry",
        "created_at",
    ]

    def get_queryset(self):

        user = self.request.user

        if user.role == UserRole.ADMIN:
            return Company.objects.all()
        elif user.role == UserRole.MANAGER:
            return Company.objects.filter(assigned_to__team=user.team)
        else:
            return Company.objects.filter(assigned_to=user)

    def perform_create(self, serializer):
        serializer.save(assigned_to=self.request.user)

    @action(detail=True, methods=["post"], url_path="add-contact")
    def add_contact(self, request, pk=None):
        company = self.get_object()
        contact_id = request.data.get("contact")
        contact_obj = get_object_or_404(Contact, id=contact_id)

        if contact_obj.company == company:
            return Response({"detail": "Контакт вже доданий до цієї компанії."})

        if contact_obj.company is not None:
            return Response({"detail": "Контакт вже доданий до іншої компанії."})

        contact_obj.company = company
        contact_obj.save()
        return Response({"detail": "Контакт додано."})

    @action(detail=True, methods=["post"], url_path="remove-contact")
    def remove_contact(self, request, pk=None):
        company = self.get_object()
        contact_id = request.data.get("contact")
        contact_obj = get_object_or_404(Contact, id=contact_id)

        if contact_obj.company != company:
            return Response({"detail": "Контакт не належить до цієї компанії."})

        contact_obj.company = None
        contact_obj.save()
        return Response({"detail": "Контакт видалено."})


class ContactViewSet(ModelViewSet):
    serializer_class = ContactSerializer
    permission_classes = [IsSalesRep]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ContactFilter
    search_fields = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "city",
        "status"
    ]
    # sorting
    ordering_fields = [
        "first_name",
        "last_name",
        "created_at",
    ]

    def get_queryset(self):

        user = self.request.user

        if user.role == UserRole.ADMIN:
            return Contact.objects.all()
        elif user.role == UserRole.MANAGER:
            return Contact.objects.filter(assigned_to__team=user.team)
        else:
            return Contact.objects.filter(assigned_to=user)

    def perform_create(self, serializer):
        serializer.save(assigned_to=self.request.user)


class ContactImportView(APIView):
    permission_classes = [IsSalesRep]
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "Файл не надано."}, status=400)

        resource = ContactResource()
        resource.assigned_to = request.user

        dataset = Dataset()
        dataset.load(file.read().decode("utf-8"), format="csv")

        result = resource.import_data(dataset, dry_run=True)

        if result.has_errors():
            return Response({"detail": "Помилки в файлі.", "errors": str(result)}, status=400)

        resource.import_data(dataset, dry_run=False)
        return Response({
            "created": result.totals["new"],
            "updated": result.totals["update"],
            "skipped": result.totals["skip"],
        })


class ContactExportView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        user = self.request.user

        export_format = request.query_params.get("file_format", "csv")

        queryset = Contact.objects.filter(assigned_to__team=user.team)

        assigned_to = request.query_params.get("assigned_to")
        if assigned_to:
            queryset = queryset.filter(assigned_to=assigned_to)

        status = request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)

        # експорт
        resource = ContactResource()
        dataset = resource.export(queryset)

        if export_format == "excel":
            content = dataset.xlsx
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = "contacts.xlsx"
        else:
            content = dataset.csv.encode("utf-8")
            content_type = "text/csv"
            filename = "contacts.csv"

        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class ProductViewSet(ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.all()

    def get_permissions(self):
        if self.action in [
            "list",  # GET
            "retrieve",  # GET id
        ]:
            return [IsSalesRep()]
        return [IsManager()]


class PipelineViewSet(ModelViewSet):
    serializer_class = PipelineSerializer
    permission_classes = [IsSalesRep]

    def get_queryset(self):

        user = self.request.user

        if user.role == UserRole.ADMIN:
            return Pipeline.objects.all()
        elif user.role == UserRole.MANAGER:
            return Pipeline.objects.filter(assigned_to__team=user.team)
        else:
            return Pipeline.objects.filter(assigned_to=user)

    def perform_create(self, serializer):
        serializer.save(assigned_to=self.request.user)


class DealViewSet(ModelViewSet):
    serializer_class = DealSerializer
    permission_classes = [IsSalesRep]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = DealFilter
    search_fields = [
        "name",
    ]
    # sorting
    ordering_fields = [
        "name",
        "expected_close_date",
        "amount",
        "created_at",
    ]

    def get_queryset(self):

        user = self.request.user

        if user.role == UserRole.ADMIN:
            return Deal.objects.all()
        elif user.role == UserRole.MANAGER:
            return Deal.objects.filter(assigned_to__team=user.team)
        else:
            return Deal.objects.filter(assigned_to=user)

    def perform_create(self, serializer):
        serializer.save(assigned_to=self.request.user)

    @action(detail=True, methods=["post"], url_path="change-stage")
    def change_stage(self, request, pk=None):
        deal = self.get_object()

        if deal.is_final:
            return Response({"detail": "Неможливо змінити stage завершеної угоди."}, status=400)

        if deal.status == DealStatus.ON_HOLD:
            return Response({"detail": "Неможливо змінити stage. Угода на паузі."}, status=400)

        # перевірка чи stage є в PipelineStage
        serializer = ChangeStageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_stage = serializer.validated_data["stage"]

        if deal.stage == new_stage:
            # якщо stage не змінився - не буде внесено змін до бд і не спрацює signal log_stage_change
            return Response(DealSerializer(deal).data)

        deal.stage = new_stage

        deal.is_final = new_stage in (PipelineStage.CLOSED_WON, PipelineStage.CLOSED_LOST)

        # змінюємо статус угоди, відповідно до нового stage
        if new_stage == PipelineStage.NEW_LEAD:
            deal.status = DealStatus.NEW
        elif new_stage == PipelineStage.NEGOTIATION:
            deal.status = DealStatus.NEGOTIATION
        elif new_stage == PipelineStage.CLOSED_WON:
            deal.status = DealStatus.WON
        elif new_stage == PipelineStage.CLOSED_LOST:
            deal.status = DealStatus.LOST
        else:
            deal.status = DealStatus.IN_PROGRESS

        deal._changed_by = request.user  # for signal log_stage_change
        # при збереженні спрацює signal
        deal.save()

        # повертає оновлений об'єкт
        return Response(DealSerializer(deal).data)

    @action(detail=True, methods=["post"], url_path="hold")
    def hold(self, request, pk=None):
        deal = self.get_object()

        if deal.is_final:
            return Response({"detail": "Неможливо змінити статус завершеної угоди."}, status=400)

        if deal.status == DealStatus.ON_HOLD:
            if deal.stage == PipelineStage.NEW_LEAD:
                deal.status = DealStatus.NEW
            elif deal.stage == PipelineStage.NEGOTIATION:
                deal.status = DealStatus.NEGOTIATION
            else:
                deal.status = DealStatus.IN_PROGRESS
        else:
            deal.status = DealStatus.ON_HOLD

        deal.save()

        # повертає оновлений об'єкт
        return Response(DealSerializer(deal).data)

    @action(detail=True, methods=["get"], url_path="stage-history")
    def stage_history(self, request, pk=None):
        deal = self.get_object()
        history = deal.stage_history.all().order_by("-changed_at")
        serializer = DealStageHistorySerializer(history, many=True)
        return Response(serializer.data)
