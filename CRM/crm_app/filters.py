import django_filters
from .models import Company, Contact


class ContactFilter(django_filters.FilterSet):
    class Meta:
        model = Contact
        fields = ["city", "assigned_to", "status", "company", "lead_source"]


class CompanyFilter(django_filters.FilterSet):
    class Meta:
        model = Company
        fields = ["industry", "assigned_to"]
