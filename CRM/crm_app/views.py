from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import PermissionDenied, MethodNotAllowed
from tablib import Dataset
from django.db.models import Q

from .permissions import IsSalesRep, IsManager
from auth_app.models import UserRole, User
from .models import (
    Company,
    Contact,
    Product,
    Deal,
    Pipeline,
    PipelineStage,
    DealStatus,
    Activity,
    Notification,
    ActivityScript,
)
from .serializers import (
    CompanySerializer,
    ContactSerializer,
    ProductSerializer,
    PipelineSerializer,
    DealSerializer,
    ChangeStageSerializer,
    DealStageHistorySerializer,
    ActivitySerializer,
    ActivityLogSerializer,
    NotificationSerializer,
    ActivityScriptSerializer,
)
from .filters import ContactFilter, CompanyFilter, DealFilter, ActivityFilter, ActivityScriptFilter
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
        if user.role == UserRole.MANAGER:
            return Company.objects.filter(assigned_to__team=user.team)
        if user.role == UserRole.SALES_REP:
            return Company.objects.filter(assigned_to=user)

        return Company.objects.none()

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
        if user.role == UserRole.MANAGER:
            return Contact.objects.filter(assigned_to__team=user.team)
        if user.role == UserRole.SALES_REP:
            return Contact.objects.filter(assigned_to=user)

        return Contact.objects.none()

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
        if user.role == UserRole.MANAGER:
            return Pipeline.objects.filter(assigned_to__team=user.team)
        if user.role == UserRole.SALES_REP:
            return Pipeline.objects.filter(assigned_to=user)

        return Pipeline.objects.none()

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
        if user.role == UserRole.MANAGER:
            return Deal.objects.filter(assigned_to__team=user.team)
        if user.role == UserRole.SALES_REP:
            return Deal.objects.filter(assigned_to=user)

        return Deal.objects.none()

    def perform_create(self, serializer):
        # щоб product угоди був такий, як в pipeline, до якої вона належить
        pipeline_id = self.request.data['pipeline']
        product = Pipeline.objects.get(id=pipeline_id).product

        serializer.save(assigned_to=self.request.user, product=product)

    @action(detail=True, methods=["post"], url_path="change-stage")
    def change_stage(self, request, pk=None):
        deal = self.get_object()

        if deal.closed_at:
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

        if new_stage in (PipelineStage.CLOSED_WON, PipelineStage.CLOSED_LOST):
            deal.closed_at = timezone.now()

        # змінюємо статус угоди, відповідно до нового stage
        if new_stage == PipelineStage.NEW_LEAD:
            deal.status = DealStatus.NEW
        elif new_stage in (PipelineStage.CLOSED_WON, PipelineStage.CLOSED_LOST):
            deal.status = DealStatus.CLOSED
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

        if deal.closed_at:
            return Response({"detail": "Неможливо змінити статус завершеної угоди."}, status=400)

        if deal.status == DealStatus.ON_HOLD:
            if deal.stage == PipelineStage.NEW_LEAD:
                deal.status = DealStatus.NEW
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

    @action(detail=True, methods=["post"], url_path="add-contact")
    def add_contact(self, request, pk=None):
        deal = self.get_object()
        contact_id = request.data.get("contact")
        contact = get_object_or_404(Contact, id=contact_id)

        deal.contacts.add(contact)
        return Response({"detail": "Контакт додано."})

    @action(detail=True, methods=["post"], url_path="remove-contact")
    def remove_contact(self, request, pk=None):
        deal = self.get_object()
        contact_id = request.data.get("contact")
        contact = get_object_or_404(Contact, id=contact_id)

        deal.contacts.remove(contact)
        return Response({"detail": "Контакт видалено."})


class ActivityViewSet(ModelViewSet):
    serializer_class = ActivitySerializer
    permission_classes = [IsSalesRep]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ActivityFilter
    search_fields = [
        "title",
        'activity_type',
    ]
    # sorting
    ordering_fields = [
        "title",
        "created_at",
        "due_date",
        "completed_at",
    ]

    def get_queryset(self):

        user = self.request.user

        if user.role == UserRole.ADMIN:
            return Activity.objects.all()
        if user.role == UserRole.MANAGER:
            return Activity.objects.filter(assigned_to__team=user.team)
        if user.role == UserRole.SALES_REP:
            return Activity.objects.filter(assigned_to=user)

        return Activity.objects.none()

    def perform_create(self, serializer):
        # дозволяє Manager і Admin вказувати assigned_to при створенні
        assigned_to_id = self.request.data.get("assigned_to")
        user = self.request.user

        if assigned_to_id:
            assigned_to = User.objects.get(id=assigned_to_id)
            if user.role == UserRole.ADMIN:
                serializer.save(assigned_to=assigned_to)
            elif user.team == assigned_to.team:
                # Manager може створити активність тільки для Sales Rep своєї команди
                serializer.save(assigned_to=assigned_to)
            else:
                raise PermissionDenied("You can create activities only for members of your own team.")

        else:
            # якщо не вказано assigned_to при створенні
            serializer.save(assigned_to=user)

    def perform_update(self, serializer):
        # для передавання _changed_by у signal
        serializer.instance._changed_by = self.request.user
        serializer.save()

    @action(detail=True, methods=["post"], url_path="mark-as-completed")
    def mark_as_completed(self, request, pk=None):
        activity = self.get_object()

        if activity.completed_at is None:
            activity._changed_by = request.user
            activity.completed_at = timezone.now()
            activity.save(update_fields=["completed_at"])

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="activity-log")
    def activity_log(self, request, pk=None):
        activity = self.get_object()
        activity_log = activity.activity_log.all().order_by("-timestamp")
        serializer = ActivityLogSerializer(activity_log, many=True)
        return Response(serializer.data)


class NotificationViewSet(ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsSalesRep]

    filter_backends = [OrderingFilter]
    # sorting
    ordering_fields = [
        "notify_at",
        "sent_at",
        "read_at",
    ]

    def get_queryset(self):
        user = self.request.user

        return Notification.objects.filter(recipient=user, sent_at__isnull=False)

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed("POST")

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT")

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PATCH")

    @action(detail=True, methods=["post"], url_path="mark-as-read")
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()

        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])

        return Response(status=status.HTTP_204_NO_CONTENT)


class ActivityScriptViewSet(ModelViewSet):
    serializer_class = ActivityScriptSerializer
    permission_classes = [IsSalesRep]

    # для attachment
    parser_classes = [MultiPartParser, FormParser]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ActivityScriptFilter
    search_fields = [
        "title",
        'activity_type',
        'stage',
        'product',
    ]
    # sorting
    ordering_fields = [
        "title",
        "activity_type",
        "stage",
        "product",
    ]

    def get_queryset(self):

        user = self.request.user

        if user.role == UserRole.ADMIN:
            return ActivityScript.objects.all()

        if user.role == UserRole.MANAGER:
            # всі, які створили адміни, і команда менеджера
            return ActivityScript.objects.filter(
                Q(created_by__role=UserRole.ADMIN) |
                Q(created_by__team=user.team)
            ).distinct()

        if user.role == UserRole.SALES_REP:
            # всі, які створили адміни, менеджер команди, до якої належить Sales, і ті, які створив сам Sales
            return ActivityScript.objects.filter(
                Q(created_by__role=UserRole.ADMIN) |
                Q(created_by__team=user.team, created_by__role=UserRole.MANAGER) |
                Q(created_by=user)
            ).distinct()

        return ActivityScript.objects.none()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
