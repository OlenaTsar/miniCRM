import django_filters
from .models import Company, Contact, Deal


class ContactFilter(django_filters.FilterSet):
    class Meta:
        model = Contact
        fields = ["city", "assigned_to", "status", "company", "lead_source"]


class CompanyFilter(django_filters.FilterSet):
    class Meta:
        model = Company
        fields = ["industry", "assigned_to"]


class DealFilter(django_filters.FilterSet):
    # звичайний фільтр для amount=
    amount = django_filters.NumberFilter(field_name="amount", lookup_expr="exact")
    # створює amount_min і amount_max, для фільтрування за мінімальною і максимальною ціною
    amount_min = django_filters.NumberFilter(field_name="amount", lookup_expr="gte")
    amount_max = django_filters.NumberFilter(field_name="amount", lookup_expr="lte")

    class Meta:
        model = Deal
        fields = [
            'status',
            'stage',
            'product',
            'expected_close_date',
            'assigned_to',
            'created_at',
            'pipeline',
            'amount',
            'amount_min',
            'amount_max',
        ]
