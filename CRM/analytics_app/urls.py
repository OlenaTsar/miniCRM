from django.urls import path

from .views import (
    DealsAnalyticsView,
    DealsByPipelineAnalyticsView,
    DealsByTeamsAnalyticsView,
    ActivitiesAnalyticsView,
    ActivitiesByPipelineAnalyticsView,
    ActivitiesByTeamsAnalyticsView,
    ContactsAnalyticsView,
    ContactsByPipelineAnalyticsView,
    ContactsByTeamsAnalyticsView,
    TeamsAnalyticsView,
    DashboardAnalyticsView,
    MyDashboardAnalyticsView,
)

urlpatterns = [
    path("deals/", DealsAnalyticsView.as_view()),
    path("deals/by-pipeline/", DealsByPipelineAnalyticsView.as_view()),
    path("deals/by-teams/", DealsByTeamsAnalyticsView.as_view()),
    path("activities/", ActivitiesAnalyticsView.as_view()),
    path("activities/by-pipeline/", ActivitiesByPipelineAnalyticsView.as_view()),
    path("activities/by-teams/", ActivitiesByTeamsAnalyticsView.as_view()),
    path("contacts/", ContactsAnalyticsView.as_view()),
    path("contacts/by-pipeline/", ContactsByPipelineAnalyticsView.as_view()),
    path("contacts/by-teams/", ContactsByTeamsAnalyticsView.as_view()),
    path("teams/", TeamsAnalyticsView.as_view()),
    path("dashboard/", DashboardAnalyticsView.as_view()),
    path("dashboard/my/", MyDashboardAnalyticsView.as_view()),
]
