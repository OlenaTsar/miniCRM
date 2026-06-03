from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .permissions import IsSalesRep
from auth_app.models import UserRole
from .models import Company, Contact
from .serializers import CompanySerializer, ContactSerializer
from .filters import ContactFilter, CompanyFilter


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
