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
    # автоматично створює amount_min і amount_max, для фільтрування за мінімальною і максимальною ціною
    amount = django_filters.RangeFilter()

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
        ]
