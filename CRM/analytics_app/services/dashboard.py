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

    def get_data(self):
        result = dict()

        result['deals'] = DealAnalyticsService(request=self.request, deals=self.user.deals).get_data()
        result['activities'] = ActivityAnalyticsService(
            request=self.request,
            activities=self.user.activities
        ).get_data()
        result['contacts'] = ContactAnalyticsService(request=self.request, contacts=self.user.contacts).get_data()

        return result
