from datetime import timedelta

import pytest
from django.utils import timezone

from crm_app.tests.factories import (PipelineFactory,
                        DealFactory,
                        ActivityFactory)
from crm_app.models import PipelineStage, DealStatus, Activity, ActivityType, Deal
from auth_app.tests.factories import UserFactory


@pytest.mark.django_db
class TestAnalyticsActivitiesEndpoint:
    # /api/analytics/activities/
    # GET
    def test_admin_can_get_activities_analytics(self, admin_client):
        ActivityFactory.create_batch(3)
        res = admin_client.get("/api/analytics/activities/")
        assert res.status_code == 200

    def test_manager_can_get_analytics_only_for_own_team_activities(self, manager_client, manager_user):
        # activities, що не належать користувачам з команди менеджера
        ActivityFactory.create_batch(3)
        res = manager_client.get("/api/analytics/activities/")
        assert res.status_code == 200
        assert res.data["total"] == 0

        # activities, що належать користувачам з команди менеджера
        user = UserFactory(team=manager_user.team)
        ActivityFactory.create_batch(3, assigned_to=user)
        res = manager_client.get("/api/analytics/activities/")
        assert res.status_code == 200
        assert res.data["total"] == 3

    def test_sales_rep_can_get_analytics_only_for_own_activities(self, sales_rep_client, sales_rep_user):
        # activities, що не належать sales_rep
        ActivityFactory.create_batch(3)
        res = sales_rep_client.get("/api/analytics/activities/")
        assert res.status_code == 200
        assert res.data["total"] == 0

        # activities, що належать sales_rep
        ActivityFactory.create_batch(3, assigned_to=sales_rep_user)
        res = sales_rep_client.get("/api/analytics/activities/")
        assert res.status_code == 200
        assert res.data["total"] == 3

    def test_employee_cannot_get_activities_analytics(self, employee_client):
        ActivityFactory.create_batch(3)
        res = employee_client.get("/api/analytics/activities/")
        assert res.status_code == 403

    def test_activities_analytics_data(self, admin_client):
        won_deal = DealFactory(stage=PipelineStage.CLOSED_WON)
        ActivityFactory.create_batch(3, deal=won_deal)
        completed_activity = ActivityFactory(
            completed_at=timezone.now() + timedelta(days=6),
        )
        overdue_activity = ActivityFactory(
            due_date=timezone.now() - timedelta(days=6),
        )

        res = admin_client.get("/api/analytics/activities/")
        data = res.data

        assert data["total"] == 5
        assert data["completed"] == 1
        assert data["overdue"] == 1
        assert len(data["total_by_type"]) == 1
        assert data["total_by_type"][0] == {
            "activity_type": "call",
            "count": 5,
            "completed": 1,
            "overdue": 1
        }
        assert data["avg_activities_per_won_deal"] == 3


@pytest.mark.django_db
class TestAnalyticsActivitiesByPipelineEndpoint:
    # /api/analytics/activities/by-pipeline/
    # GET
    def test_admin_can_get_activities_by_pipeline_analytics(self, admin_client):
        ActivityFactory.create_batch(3)
        res = admin_client.get("/api/analytics/activities/by-pipeline/")
        assert res.status_code == 200

    def test_manager_can_get_activities_by_pipeline_analytics_only_for_own_team(self, manager_client, manager_user):
        team_user = UserFactory(team=manager_user.team)
        team_pipeline = PipelineFactory(assigned_to=team_user)
        team_deal = DealFactory(pipeline=team_pipeline)
        team_activities = ActivityFactory.create_batch(3, deal=team_deal)

        ActivityFactory.create_batch(3)

        res = manager_client.get("/api/analytics/activities/by-pipeline/")
        assert res.status_code == 200
        assert len(res.data) == 1
        data = res.data[0]
        assert data["pipeline_name"] == team_pipeline.name
        assert data["analytics"]["total"] == 3

    def test_sales_rep_can_get_activities_by_pipeline_analytics_only_for_own_pipelines(self, sales_rep_client,
                                                                                       sales_rep_user):
        sales_rep_pipeline = PipelineFactory(assigned_to=sales_rep_user)
        sales_rep_deal = DealFactory(pipeline=sales_rep_pipeline)
        sales_rep_activities = ActivityFactory.create_batch(3, deal=sales_rep_deal)

        ActivityFactory.create_batch(3)

        res = sales_rep_client.get("/api/analytics/activities/by-pipeline/")
        assert res.status_code == 200
        assert len(res.data) == 1
        data = res.data[0]
        assert data["pipeline_name"] == sales_rep_pipeline.name
        assert data["analytics"]["total"] == 3


@pytest.mark.django_db
class TestAnalyticsActivitiesByTeamEndpoint:
    # /api/analytics/activities/by-team/
    # GET
    def test_admin_can_get_activities_by_team_analytics(self, admin_client):
        ActivityFactory.create_batch(3)
        res = admin_client.get("/api/analytics/activities/by-team/")
        assert res.status_code == 200

    def test_manager_cannot_get_activities_by_team_analytics(self, manager_client):
        ActivityFactory.create_batch(3)

        res = manager_client.get("/api/analytics/activities/by-team/")

        assert res.status_code == 403

    def test_sales_rep_cannot_get_activities_by_team_analytics(self, sales_rep_client):
        ActivityFactory.create_batch(3)

        res = sales_rep_client.get("/api/analytics/activities/by-team/")

        assert res.status_code == 403
