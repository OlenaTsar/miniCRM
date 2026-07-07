from rest_framework.views import APIView
from rest_framework.response import Response

from .permissions import IsSalesRep, IsAdmin, IsManager
from .services.deals import DealAnalyticsService, DealByPipelineAnalyticsService, DealByTeamsAnalyticsService
from .services.activities import (
    ActivityAnalyticsService,
    ActivityByPipelineAnalyticsService,
    ActivityByTeamsAnalyticsService
)
from .services.contacts import (
    ContactAnalyticsService,
    ContactByPipelineAnalyticsService,
    ContactByTeamsAnalyticsService
)
from .services.teams import TeamAnalyticsService
from .services.dashboard import DashboardAnalyticsService, MyDashboardAnalyticsService
from .serializers import (
    DealAnalyticsSerializer,
    DealByPipelineAnalyticsSerializer,
    DealByTeamsAnalyticsSerializer,
    ActivityAnalyticsSerializer,
    ActivityByPipelineAnalyticsSerializer,
    ActivityByTeamsAnalyticsSerializer,
    ContactAnalyticsSerializer,
    ContactByPipelineAnalyticsSerializer,
    ContactByTeamsAnalyticsSerializer,
    TeamAnalyticsSerializer,
    DashboardAnalyticsSerializer,
)


class DealsAnalyticsView(APIView):
    permission_classes = [IsSalesRep]

    def get(self, request):
        data = DealAnalyticsService(request).get_data()
        serializer = DealAnalyticsSerializer(data)

        return Response(serializer.data)


class DealsByPipelineAnalyticsView(APIView):
    permission_classes = [IsSalesRep]

    def get(self, request):
        data = DealByPipelineAnalyticsService(request).get_data()
        serializer = DealByPipelineAnalyticsSerializer(data, many=True)

        return Response(serializer.data)


class DealsByTeamsAnalyticsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        data = DealByTeamsAnalyticsService(request).get_data()
        serializer = DealByTeamsAnalyticsSerializer(data, many=True)

        return Response(serializer.data)


class ActivitiesAnalyticsView(APIView):
    permission_classes = [IsSalesRep]

    def get(self, request):
        data = ActivityAnalyticsService(request).get_data()
        serializer = ActivityAnalyticsSerializer(data)

        return Response(serializer.data)


class ActivitiesByPipelineAnalyticsView(APIView):
    permission_classes = [IsSalesRep]

    def get(self, request):
        data = ActivityByPipelineAnalyticsService(request).get_data()
        serializer = ActivityByPipelineAnalyticsSerializer(data, many=True)

        return Response(serializer.data)


class ActivitiesByTeamsAnalyticsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        data = ActivityByTeamsAnalyticsService(request).get_data()
        serializer = ActivityByTeamsAnalyticsSerializer(data, many=True)

        return Response(serializer.data)


class ContactsAnalyticsView(APIView):
    permission_classes = [IsSalesRep]

    def get(self, request):
        data = ContactAnalyticsService(request).get_data()
        serializer = ContactAnalyticsSerializer(data)

        return Response(serializer.data)


class ContactsByPipelineAnalyticsView(APIView):
    permission_classes = [IsSalesRep]

    def get(self, request):
        data = ContactByPipelineAnalyticsService(request).get_data()
        serializer = ContactByPipelineAnalyticsSerializer(data, many=True)

        return Response(serializer.data)


class ContactsByTeamsAnalyticsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        data = ContactByTeamsAnalyticsService(request).get_data()
        serializer = ContactByTeamsAnalyticsSerializer(data, many=True)

        return Response(serializer.data)


class TeamsAnalyticsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        data = TeamAnalyticsService(request).get_data()
        serializer = TeamAnalyticsSerializer(data, many=True)

        return Response(serializer.data)


class DashboardAnalyticsView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        data = DashboardAnalyticsService(request).get_data()
        serializer = DashboardAnalyticsSerializer(data)

        return Response(serializer.data)


class MyDashboardAnalyticsView(APIView):
    permission_classes = [IsSalesRep]

    def get(self, request):
        data = MyDashboardAnalyticsService(request).get_data()
        serializer = DashboardAnalyticsSerializer(data)

        return Response(serializer.data)
