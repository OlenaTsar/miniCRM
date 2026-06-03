from django.http import HttpResponse
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
from .models import Company, Contact
from .serializers import CompanySerializer, ContactSerializer
from .filters import ContactFilter, CompanyFilter
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
            return Company.objects.filter(user__team=user.team)
        else:
            return Company.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="add-contact")
    def add_user(self, request, pk=None):
        company = self.get_object()
        contact_id = request.data.get("contact")
        contact_obj = Contact.objects.get(id=contact_id)

        if contact_obj.company == company:
            return Response({"detail": "Контакт вже доданий до цієї компанії."})

        if contact_obj.company is not None:
            return Response({"detail": "Контакт вже доданий до іншої компанії."})

        contact_obj.company = company
        contact_obj.save()
        return Response({"detail": "Контакт додано."})

    @action(detail=True, methods=["post"], url_path="remove-contact")
    def remove_user(self, request, pk=None):
        company = self.get_object()
        contact_id = request.data.get("contact")
        contact_obj = Contact.objects.get(id=contact_id)

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
            return Contact.objects.filter(user__team=user.team)
        else:
            return Contact.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ContactImportView(APIView):
    permission_classes = [IsSalesRep]
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "Файл не надано."}, status=400)

        resource = ContactResource()
        resource.user = request.user

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
        print("format:", request.query_params.get("file_format"))
        print("user:", request.user)
        print("user role:", request.user.role)
        user = self.request.user

        export_format = request.query_params.get("file_format", "csv")

        queryset = Contact.objects.filter(user__team=user.team)

        assigned_to = request.query_params.get("assigned_to")
        if assigned_to:
            queryset = queryset.filter(user=assigned_to)

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
