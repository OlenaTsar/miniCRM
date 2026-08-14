import django_filters
from .models import Company, Contact, Deal, Activity, ActivityScript, Archive


class ContactFilter(django_filters.FilterSet):
    class Meta:
        model = Contact
        fields = ["city", "created_by", "status", "company", "lead_source"]


class CompanyFilter(django_filters.FilterSet):
    class Meta:
        model = Company
        fields = ["industry", "created_by"]


class DealFilter(django_filters.FilterSet):
    # звичайний фільтр для amount=
    amount = django_filters.NumberFilter(field_name="amount", lookup_expr="exact")
    # створює amount_min і amount_max, для фільтрування за мінімальною і максимальною ціною
    amount_min = django_filters.NumberFilter(field_name="amount", lookup_expr="gte")
    amount_max = django_filters.NumberFilter(field_name="amount", lookup_expr="lte")

    # фільтр для діапазону дат (created_at_after= created_at_before=)
    created_at = django_filters.DateFromToRangeFilter(field_name="created_at")
    expected_close_date = django_filters.DateFromToRangeFilter(field_name="expected_close_date")

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


class ActivityFilter(django_filters.FilterSet):
    class Meta:
        model = Activity
        fields = [
            'activity_type',
            'created_at',
            'due_date',
            'completed_at',
            'assigned_to',
            'contact',
            'deal',
        ]


class ActivityScriptFilter(django_filters.FilterSet):
    class Meta:
        model = ActivityScript
        fields = [
            'activity_type',
            'stage',
            'product',
            'created_by',
        ]


class ArchiveFilter(django_filters.FilterSet):

    # фільтр для діапазону дат (timestamp_after= timestamp_before=)
    timestamp = django_filters.DateFromToRangeFilter(field_name="timestamp")

    has_pipelines = django_filters.BooleanFilter(method="filter_has_pipelines")
    has_deals = django_filters.BooleanFilter(method="filter_has_deals")
    has_activities = django_filters.BooleanFilter(method="filter_has_activities")

    def filter_has_pipelines(self, queryset, name, value):
        if value:
            return queryset.filter(pipelines__isnull=False).distinct()
        return queryset.filter(pipelines__isnull=True)

    def filter_has_deals(self, queryset, name, value):
        if value:
            return queryset.filter(deals__isnull=False).distinct()
        return queryset.filter(deals__isnull=True)

    def filter_has_activities(self, queryset, name, value):
        if value:
            return queryset.filter(activities__isnull=False).distinct()
        return queryset.filter(activities__isnull=True)

    class Meta:
        model = Archive
        fields = [
            'archiving_type',
            'timestamp',
            'archived_by',
            'has_pipelines',
            'has_deals',
            'has_activities',
        ]
