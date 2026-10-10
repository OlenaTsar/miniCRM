from datetime import timedelta

import pytest
from django.utils import timezone

from crm_app.tests.factories import ContactFactory, PipelineFactory, DealFactory, ActivityFactory
from auth_app.tests.factories import UserFactory, TeamFactory
from crm_app.models import PipelineStage, DealStatus, Deal
from auth_app.models import UserRole


@pytest.mark.django_db
class TestAnalyticsTeamsEndpoint:
    # /api/analytics/teams/
    # GET
    def test_admin_can_get_teams_analytics(self, admin_client):
        TeamFactory.create_batch(3)
        res = admin_client.get("/api/analytics/teams/")
        assert res.status_code == 200

    def test_manager_cannot_get_teams_analytics(self, manager_client):
        TeamFactory.create_batch(3)
        res = manager_client.get("/api/analytics/teams/")
        assert res.status_code == 403

    def test_sales_rep_cannot_get_teams_analytics(self, sales_rep_client):
        TeamFactory.create_batch(3)
        res = sales_rep_client.get("/api/analytics/teams/")
        assert res.status_code == 403

    def test_employee_cannot_get_teams_analytics(self, employee_client):
        TeamFactory.create_batch(3)
        res = employee_client.get("/api/analytics/teams/")
        assert res.status_code == 403

    def test_teams_analytics_data(self, admin_client, admin_user):
        team = admin_user.team
        manager = UserFactory(team=team, role=UserRole.MANAGER)
        sales_rep = UserFactory(team=team, role=UserRole.SALES_REP)

        deals = DealFactory.create_batch(3, assigned_to=sales_rep)
        won_deal = DealFactory(
            status=DealStatus.CLOSED,
            stage=PipelineStage.CLOSED_WON,
            closed_at=timezone.now() + timedelta(days=6),
            assigned_to=sales_rep,
        )
        activities = ActivityFactory.create_batch(3, assigned_to=sales_rep, deal=won_deal)

        res = admin_client.get("/api/analytics/teams/")
        data = res.data[0]

        assert data["team_name"] == team.name
        assert data["managers"] == [manager.email]
        assert data["sales_reps"] == [sales_rep.email]
        assert data["total_deals"] == 4
        assert data["total_won_deals"] == 1
        assert data["conversion"] == 25
        assert data["amount_average_won_deals"] == float(won_deal.amount)
        assert data["completed_activities"] == 0
        assert data["overdue_activities"] == 0
        assert data["avg_activities_per_won_deal"] == 3
        assert data["average_deal_duration"] == 6
