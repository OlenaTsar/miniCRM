from .deals import DealAnalyticsService
from .activities import ActivityAnalyticsService
from .contacts import ContactAnalyticsService


class DashboardAnalyticsService:
    def __init__(self, request):
        self.request = request

    def get_data(self):
        result = dict()

        result['deals'] = DealAnalyticsService(request=self.request).get_data()
        result['activities'] = ActivityAnalyticsService(request=self.request).get_data()
        result['contacts'] = ContactAnalyticsService(request=self.request).get_data()

        return result


class MyDashboardAnalyticsService:
    def __init__(self, request):
        self.request = request
        self.user = request.user
        self.deals = self._get_deals()
        self.activities = self._get_activities()

    def _get_deals(self):
        queryset = self.user.deals

        # include archived
        include_archived = self.request.query_params.get("include_archived", "false")
        if include_archived.lower() != "true":
            queryset = queryset.filter(archived__isnull=True)

        return queryset

    def _get_activities(self):
        queryset = self.user.activities

        # include archived
        include_archived = self.request.query_params.get("include_archived", "false")
        if include_archived.lower() != "true":
            queryset = queryset.filter(archived__isnull=True)

        return queryset

    def get_data(self):
        result = dict()

        result['deals'] = DealAnalyticsService(request=self.request, deals=self.deals).get_data()
        result['activities'] = ActivityAnalyticsService(request=self.request, activities=self.activities).get_data()
        result['contacts'] = ContactAnalyticsService(request=self.request, contacts=self.user.contacts).get_data()

        return result
