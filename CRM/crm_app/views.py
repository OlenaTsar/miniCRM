from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
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
from rest_framework import mixins, viewsets
from django.db.models import Q, Prefetch

from CRM.permissions import IsSalesRep, IsManager
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
    Archive,
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
    ArchiveSerializer,
)
from .filters import ContactFilter, CompanyFilter, DealFilter, ActivityFilter, ActivityScriptFilter, ArchiveFilter
from .resources import ContactResource, ContactReportResource, DealReportResource, ActivityReportResource
from .tasks import send_data_archiving_notification


class CompanyViewSet(ModelViewSet):
    serializer_class = CompanySerializer
    permission_classes = [IsSalesRep]
    queryset = Company.objects.all()

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

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="add-contact")
    def add_contact(self, request, pk=None):
        company = self.get_object()
        contact_id = request.data.get("contact")
        contact_obj = get_object_or_404(Contact, id=contact_id)

        if contact_obj.company == company:
            return Response({"detail": "Контакт вже доданий до цієї компанії."}, status=400)

        if contact_obj.company is not None:
            return Response({"detail": "Контакт вже доданий до іншої компанії."}, status=400)

        contact_obj.company = company
        contact_obj.save()
        return Response({"detail": "Контакт додано."})

    @action(detail=True, methods=["post"], url_path="remove-contact")
    def remove_contact(self, request, pk=None):
        company = self.get_object()
        contact_id = request.data.get("contact")
        contact_obj = get_object_or_404(Contact, id=contact_id)

        if contact_obj.company != company:
            return Response({"detail": "Контакт не належить до цієї компанії."}, status=400)

        contact_obj.company = None
        contact_obj.save()
        return Response({"detail": "Контакт видалено."})


class ContactViewSet(ModelViewSet):
    serializer_class = ContactSerializer
    permission_classes = [IsSalesRep]
    queryset = Contact.objects.all()

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

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ContactImportView(APIView):
    permission_classes = [IsSalesRep]
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "Файл не надано."}, status=400)

        resource = ContactResource()
        resource.created_by = request.user

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
    permission_classes = [IsSalesRep]

    def get(self, request):
        user = self.request.user

        export_format = request.query_params.get("file_format", "csv")

        queryset = Contact.objects.all()

        created_by = request.query_params.get("created_by")
        if created_by:
            queryset = queryset.filter(created_by=created_by)

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
        display_archived = self.request.query_params.get("display_archived", "false")

        if user.role == UserRole.ADMIN:
            queryset = Pipeline.objects.all()
            if display_archived.lower() != "true":
                queryset = queryset.filter(archived__isnull=True)
            return queryset
        if user.role == UserRole.MANAGER:
            queryset = Pipeline.objects.filter(assigned_to__team=user.team)
            if display_archived.lower() != "true":
                queryset = queryset.filter(archived__isnull=True)
            return queryset
        if user.role == UserRole.SALES_REP:
            queryset = Pipeline.objects.filter(assigned_to=user)
            if display_archived.lower() != "true":
                queryset = queryset.filter(archived__isnull=True)
            return queryset

        return Pipeline.objects.none()

    def perform_create(self, serializer):
        assigned_to = serializer.validated_data.get("assigned_to")

        if assigned_to:
            serializer.save()
        else:
            serializer.save(assigned_to=self.request.user)

    def perform_update(self, serializer):
        # для передавання _changed_by у signal (ActivityLog)
        # потрібно при зміні assigned_to
        serializer.instance._changed_by = self.request.user
        serializer.save()


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
        display_archived = self.request.query_params.get("display_archived", "false")

        if user.role == UserRole.ADMIN:
            queryset = Deal.objects.all()
            if display_archived.lower() != "true":
                queryset = queryset.filter(archived__isnull=True)
            return queryset
        if user.role == UserRole.MANAGER:
            queryset = Deal.objects.filter(assigned_to__team=user.team)
            if display_archived.lower() != "true":
                queryset = queryset.filter(archived__isnull=True)
            return queryset
        if user.role == UserRole.SALES_REP:
            queryset = Deal.objects.filter(assigned_to=user)
            if display_archived.lower() != "true":
                queryset = queryset.filter(archived__isnull=True)
            return queryset

        return Deal.objects.none()

    def perform_create(self, serializer):
        pipeline = serializer.validated_data.get('pipeline')

        # щоб product угоди був той, що і в pipeline, до якої вона належить
        product = pipeline.product

        # щоб угода належала користувачеві, якому належить pipeline
        assigned_to = pipeline.assigned_to

        serializer.save(assigned_to=assigned_to, product=product)

    def perform_update(self, serializer):
        # для передавання _changed_by у signal (ActivityLog)
        # потрібно при зміні assigned_to
        serializer.instance._changed_by = self.request.user
        serializer.save()

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
            # якщо угода була на паузі - знімаємо з паузи
            if deal.stage == PipelineStage.NEW_LEAD:
                deal.status = DealStatus.NEW
            else:
                deal.status = DealStatus.IN_PROGRESS

            # відновлюємо сповіщення по угоді
            # якщо активність не завершена і не є простроченою
            now = timezone.now()
            for activity in deal.activities.filter(completed_at__isnull=True, due_date__gt=now + timedelta(minutes=1)):
                if activity.due_date <= now + timedelta(hours=1):
                    notify_at = now + timedelta(minutes=1)
                else:
                    notify_at = activity.due_date - timedelta(hours=1)

                Notification.objects.create(
                    notify_at=notify_at,
                    recipient=activity.assigned_to,
                    activity=activity
                )
        else:
            # якщо угода була активною - ставимо на паузу
            deal.status = DealStatus.ON_HOLD

            # скасовуємо сповіщення по угоді, якщо сповіщення ще не було надіслано
            notifications = Notification.objects.filter(activity__in=deal.activities.all(), sent_at__isnull=True)
            for notification in notifications:
                notification.delete()

        deal.save()

        # повертає оновлений об'єкт
        return Response(DealSerializer(deal).data)

    @action(detail=True, methods=["get"], url_path="stage-history")
    def stage_history(self, request, pk=None):
        deal = self.get_object()
        history = deal.stage_history.all().order_by("-changed_at")
        serializer = DealStageHistorySerializer(history, many=True)
        return Response(serializer.data)


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
        display_archived = self.request.query_params.get("display_archived", "false")

        if user.role == UserRole.ADMIN:
            queryset = Activity.objects.all()
            if display_archived.lower() != "true":
                queryset = queryset.filter(archived__isnull=True)
            return queryset
        if user.role == UserRole.MANAGER:
            queryset = Activity.objects.filter(assigned_to__team=user.team)
            if display_archived.lower() != "true":
                queryset = queryset.filter(archived__isnull=True)
            return queryset
        if user.role == UserRole.SALES_REP:
            queryset = Activity.objects.filter(assigned_to=user)
            if display_archived.lower() != "true":
                queryset = queryset.filter(archived__isnull=True)
            return queryset

        return Activity.objects.none()

    def perform_create(self, serializer):
        # автоматичне заповнення поля contact, відповідно до deal
        deal_id = self.request.data.get("deal")
        # не перевіряю чи deal_id існує, бо помилка повернеться швидше
        deal = Deal.objects.get(id=deal_id)
        contact = deal.contact

        # дозволяє Manager і Admin вказувати assigned_to при створенні
        # для SALES_REP заборонено передавати при створенні assigned_to у serializer
        assigned_to_id = self.request.data.get("assigned_to")
        user = self.request.user

        if assigned_to_id:
            assigned_to = User.objects.get(id=assigned_to_id)
            if user.role == UserRole.ADMIN:
                serializer.save(assigned_to=assigned_to, contact=contact)
            elif user.team == assigned_to.team:
                # Manager може створити активність тільки для Sales Rep своєї команди
                serializer.save(assigned_to=assigned_to, contact=contact)
            else:
                raise PermissionDenied("You can create activities only for members of your own team.")

        else:
            # якщо не вказано assigned_to при створенні
            serializer.save(assigned_to=user, contact=contact)

    def perform_update(self, serializer):
        # для передавання _changed_by у signal (ActivityLog)
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

        if user.role == UserRole.SALES_REP:
            if self.action in ["update", "partial_update", "destroy"]:
                return ActivityScript.objects.filter(created_by=user)
            return ActivityScript.objects.all()
        elif user.role == UserRole.MANAGER:
            if self.action in ["update", "partial_update", "destroy"]:
                return ActivityScript.objects.filter(created_by__team=user.team)
            return ActivityScript.objects.all()
        else:
            return ActivityScript.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ContactReportView(APIView):
    permission_classes = [IsSalesRep]

    def get(self, request):
        user = self.request.user

        export_format = request.query_params.get("file_format", "csv")
        queryset = Contact.objects.all()

        created_by = request.query_params.get("created_by")
        if created_by:
            queryset = queryset.filter(created_by=created_by)

        status = request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)

        # експорт
        resource = ContactReportResource()
        dataset = resource.export(queryset)
        now = timezone.now().strftime("%d.%m.%Y_%H-%M")

        if export_format == "excel":
            content = dataset.xlsx
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"contacts_report_{now}.xlsx"
        else:
            content = dataset.csv.encode("utf-8")
            content_type = "text/csv"
            filename = f"contacts_report_{now}.csv"

        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class DealReportView(APIView):
    permission_classes = [IsSalesRep]

    def get(self, request):
        user = self.request.user

        export_format = request.query_params.get("file_format", "csv")

        if user.role == UserRole.ADMIN:
            queryset = Deal.objects.all()
        elif user.role == UserRole.MANAGER:
            queryset = Deal.objects.filter(assigned_to__team=user.team)
        elif user.role == UserRole.SALES_REP:
            queryset = Deal.objects.filter(assigned_to=user)
        else:
            queryset = Deal.objects.none()

        assigned_to = request.query_params.get("assigned_to")
        if assigned_to:
            queryset = queryset.filter(assigned_to=assigned_to)

        status = request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)

        # експорт
        resource = DealReportResource()
        dataset = resource.export(queryset)
        now = timezone.now().strftime("%d.%m.%Y_%H-%M")

        if export_format == "excel":
            content = dataset.xlsx
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"deals_report_{now}.xlsx"
        else:
            content = dataset.csv.encode("utf-8")
            content_type = "text/csv"
            filename = f"deals_report_{now}.csv"

        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class ActivityReportView(APIView):
    permission_classes = [IsSalesRep]

    def get(self, request):
        user = self.request.user

        export_format = request.query_params.get("file_format", "csv")

        if user.role == UserRole.ADMIN:
            queryset = Activity.objects.all()
        elif user.role == UserRole.MANAGER:
            queryset = Activity.objects.filter(assigned_to__team=user.team)
        elif user.role == UserRole.SALES_REP:
            queryset = Activity.objects.filter(assigned_to=user)
        else:
            queryset = Activity.objects.none()

        assigned_to = request.query_params.get("assigned_to")
        if assigned_to:
            queryset = queryset.filter(assigned_to=assigned_to)

        status = request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)

        # експорт
        resource = ActivityReportResource()
        dataset = resource.export(queryset)
        now = timezone.now().strftime("%d.%m.%Y_%H-%M")

        if export_format == "excel":
            content = dataset.xlsx
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"activities_report_{now}.xlsx"
        else:
            content = dataset.csv.encode("utf-8")
            content_type = "text/csv"
            filename = f"activities_report_{now}.csv"

        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class ArchiveViewSet(
    mixins.ListModelMixin,      # GET /api/archive/
    mixins.RetrieveModelMixin,  # GET /api/archive/{id}/
    mixins.DestroyModelMixin,   # DELETE /api/archive/{id}/
    mixins.CreateModelMixin,    # POST /api/archive/
    viewsets.GenericViewSet,
):
    serializer_class = ArchiveSerializer
    permission_classes = [IsSalesRep]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ArchiveFilter
    search_fields = [
        "archiving_type",
        'timestamp',
        'archived_by',
    ]
    # sorting
    ordering_fields = [
        "archiving_type",
        'timestamp',
        'archived_by',
    ]

    def get_queryset(self):

        user = self.request.user

        if user.role == UserRole.ADMIN:
            return Archive.objects.all()
        elif user.role == UserRole.MANAGER:
            return Archive.objects.filter(
                Q(deals__assigned_to__team=user.team) |
                Q(activities__assigned_to__team=user.team) |
                Q(pipelines__assigned_to__team=user.team)
            ).prefetch_related(
                Prefetch(
                    "deals",
                    queryset=Deal.objects.filter(assigned_to__team=user.team),
                ),
                Prefetch(
                    "activities",
                    queryset=Activity.objects.filter(assigned_to__team=user.team),
                ),
                Prefetch(
                    "pipelines",
                    queryset=Pipeline.objects.filter(assigned_to__team=user.team),
                ),
            ).distinct()
        elif user.role == UserRole.SALES_REP:
            return Archive.objects.filter(
                Q(deals__assigned_to=user) |
                Q(activities__assigned_to=user) |
                Q(pipelines__assigned_to=user)
            ).prefetch_related(
                Prefetch(
                    "deals",
                    queryset=Deal.objects.filter(assigned_to=user),
                ),
                Prefetch(
                    "activities",
                    queryset=Activity.objects.filter(assigned_to=user),
                ),
                Prefetch(
                    "pipelines",
                    queryset=Pipeline.objects.filter(assigned_to=user),
                ),
            ).distinct()
        else:
            return Archive.objects.none()

    def perform_create(self, serializer):
        archive = serializer.save(archived_by=self.request.user)

        # встановлюємо зв'язок з архівом через Pipeline, Deal, Activity
        pipelines_id = self.request.data.get("pipelines", [])
        deals_id = self.request.data.get("deals", [])
        activities_id = self.request.data.get("activities", [])

        if self.request.user.role == UserRole.ADMIN:
            # перевіряє чи дані не є вже заархівованими
            pipelines = Pipeline.objects.filter(id__in=pipelines_id, archived__isnull=True)
            for pipeline in pipelines:
                pipeline.archived = archive
                pipeline.save()
            # спрацює сигнал на архівацію pipelines і всі deals і activities,
            # що належать цим pipelines будуть також архівовані

            deals = Deal.objects.filter(id__in=deals_id, archived__isnull=True)
            for deal in deals:
                deal.archived = archive
                deal.save()
            # спрацює сигнал на архівацію deals і всі activities,
            # що належать цим deals будуть також архівовані

            activities = Activity.objects.filter(id__in=activities_id, archived__isnull=True)
            for activity in activities:
                activity.archived = archive
                activity.save()

        elif self.request.user.role == UserRole.MANAGER:
            pipelines = Pipeline.objects.filter(
                id__in=pipelines_id,
                archived__isnull=True,
                assigned_to__team=self.request.user.team
            )
            for pipeline in pipelines:
                pipeline.archived = archive
                pipeline.save()

            deals = Deal.objects.filter(
                id__in=deals_id,
                archived__isnull=True,
                assigned_to__team=self.request.user.team
            )
            for deal in deals:
                deal.archived = archive
                deal.save()

            activities = Activity.objects.filter(
                id__in=activities_id,
                archived__isnull=True,
                assigned_to__team=self.request.user.team
            )
            for activity in activities:
                activity.archived = archive
                activity.save()

        elif self.request.user.role == UserRole.SALES_REP:
            pipelines = Pipeline.objects.filter(
                id__in=pipelines_id,
                archived__isnull=True,
                assigned_to=self.request.user
            )
            for pipeline in pipelines:
                pipeline.archived = archive
                pipeline.save()

            deals = Deal.objects.filter(
                id__in=deals_id,
                archived__isnull=True,
                assigned_to=self.request.user
            )
            for deal in deals:
                deal.archived = archive
                deal.save()

            activities = Activity.objects.filter(
                id__in=activities_id,
                archived__isnull=True,
                assigned_to=self.request.user
            )
            for activity in activities:
                activity.archived = archive
                activity.save()

        # надсилання користувачам сповіщення про архівацію
        users = User.objects.filter(
            Q(pipelines__archived=archive) |
            Q(deals__archived=archive) |
            Q(activities__archived=archive)
        ).distinct()

        for user in users:
            send_data_archiving_notification.delay(str(user.id), str(archive.id))

    @action(detail=False, methods=["post"], url_path="unarchive")
    def unarchive(self, request, pk=None):
        # розархівовує дані, які були передані

        pipelines_id = self.request.data.get("pipelines", [])
        deals_id = self.request.data.get("deals", [])
        activities_id = self.request.data.get("activities", [])

        if self.request.user.role == UserRole.ADMIN:
            # перевіряє чи дані є заархівованими
            pipelines = Pipeline.objects.filter(id__in=pipelines_id, archived__isnull=False)
            for pipeline in pipelines:
                pipeline.archived = None
                pipeline.save()
            # спрацює сигнал на деархівацію pipelines і всі deals і activities,
            # що належать цим pipelines, і є з ними в одному архіві, будуть також архівовані

            deals = Deal.objects.filter(id__in=deals_id, archived__isnull=False)
            for deal in deals:
                deal.archived = None
                deal.save()
            # спрацює сигнал на деархівацію deals і всі activities,
            # що належать цим deals, і є з ними в одному архіві, будуть також деархівовані

            activities = Activity.objects.filter(id__in=activities_id, archived__isnull=False)
            for activity in activities:
                activity.archived = None
                activity.save()

        elif self.request.user.role == UserRole.MANAGER:
            pipelines = Pipeline.objects.filter(
                id__in=pipelines_id,
                archived__isnull=False,
                assigned_to__team=self.request.user.team
            )
            for pipeline in pipelines:
                pipeline.archived = None
                pipeline.save()

            deals = Deal.objects.filter(
                id__in=deals_id,
                archived__isnull=False,
                assigned_to__team=self.request.user.team
            )
            for deal in deals:
                deal.archived = None
                deal.save()

            activities = Activity.objects.filter(
                id__in=activities_id,
                archived__isnull=False,
                assigned_to__team=self.request.user.team
            )
            for activity in activities:
                activity.archived = None
                activity.save()

        elif self.request.user.role == UserRole.SALES_REP:
            pipelines = Pipeline.objects.filter(
                id__in=pipelines_id,
                archived__isnull=False,
                assigned_to=self.request.user
            )
            for pipeline in pipelines:
                pipeline.archived = None
                pipeline.save()

            deals = Deal.objects.filter(
                id__in=deals_id,
                archived__isnull=False,
                assigned_to=self.request.user
            )
            for deal in deals:
                deal.archived = None
                deal.save()

            activities = Activity.objects.filter(
                id__in=activities_id,
                archived__isnull=False,
                assigned_to=self.request.user
            )
            for activity in activities:
                activity.archived = None
                activity.save()

        return Response(status=status.HTTP_204_NO_CONTENT)
