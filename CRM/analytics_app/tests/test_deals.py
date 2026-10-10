from datetime import timedelta

import pytest
from django.utils import timezone

from crm_app.tests.factories import PipelineFactory, DealFactory, ActivityFactory
from crm_app.models import PipelineStage, DealStatus, Deal
from auth_app.tests.factories import UserFactory


@pytest.mark.django_db
class TestAnalyticsDealsEndpoint:
    # /api/analytics/deals/
    # GET
    def test_admin_can_get_deals_analytics(self, admin_client):
        DealFactory.create_batch(3)
        res = admin_client.get("/api/analytics/deals/")
        assert res.status_code == 200

    def test_manager_can_get_analytics_only_for_own_team_deals(self, manager_client, manager_user):
        # угоди, що не належать користувачам з команди менеджера
        DealFactory.create_batch(3)
        res = manager_client.get("/api/analytics/deals/")
        assert res.status_code == 200
        assert res.data["total"] == 0

        # угоди, що належать користувачам з команди менеджера
        user = UserFactory(team=manager_user.team)
        DealFactory.create_batch(3, assigned_to=user)
        res = manager_client.get("/api/analytics/deals/")
        assert res.status_code == 200
        assert res.data["total"] == 3

    def test_sales_rep_can_get_analytics_only_for_own_deals(self, sales_rep_client, sales_rep_user):
        # угоди, що не належать sales_rep
        DealFactory.create_batch(3)
        res = sales_rep_client.get("/api/analytics/deals/")
        assert res.status_code == 200
        assert res.data["total"] == 0

        # угоди, що належать sales_rep
        DealFactory.create_batch(3, assigned_to=sales_rep_user)
        res = sales_rep_client.get("/api/analytics/deals/")
        assert res.status_code == 200
        assert res.data["total"] == 3

    def test_employee_cannot_get_deals_analytics(self, employee_client):
        DealFactory.create_batch(3)
        res = employee_client.get("/api/analytics/deals/")
        assert res.status_code == 403

    def test_deals_analytics_data(self, admin_client):
        # тут тестуються усі дані, окрім by_stage
        DealFactory.create_batch(3)
        won_deal_1 = DealFactory(
            status=DealStatus.CLOSED,
            stage=PipelineStage.CLOSED_WON,
            closed_at=timezone.now() + timedelta(days=6),
        )
        won_deal_2 = DealFactory(
            status=DealStatus.CLOSED,
            stage=PipelineStage.CLOSED_WON,
            closed_at=timezone.now() + timedelta(days=11),
        )
        lost_deal = DealFactory(
            status=DealStatus.CLOSED,
            stage=PipelineStage.CLOSED_LOST,
            closed_at=timezone.now() + timedelta(days=4),
        )

        res = admin_client.get("/api/analytics/deals/")
        data = res.data

        assert data["total"] == 6
        assert data["won"] == 2
        assert data["lost"] == 1
        assert data["total_conversion"] == 33.33
        assert data["amount_average_won_deals"] == float(round((won_deal_1.amount + won_deal_2.amount) / 2, 2))
        assert data["average_deal_duration"] == 7

    def test_deals_analytics_by_stage_data(self, admin_client):
        # тут тестується by_stage
        new_deal = DealFactory(
            status=DealStatus.NEW,
            stage=PipelineStage.NEW_LEAD,
        )
        qualification_deal = DealFactory(
            status=DealStatus.IN_PROGRESS,
            stage=PipelineStage.QUALIFICATION,
        )
        proposal_sent_deal = DealFactory(
            status=DealStatus.IN_PROGRESS,
            stage=PipelineStage.PROPOSAL_SENT,
        )
        on_hold_deal = DealFactory(
            status=DealStatus.ON_HOLD,
            stage=PipelineStage.PROPOSAL_SENT,
        )
        negotiation_deal = DealFactory(
            status=DealStatus.IN_PROGRESS,
            stage=PipelineStage.NEGOTIATION,
        )
        won_deal = DealFactory(
            status=DealStatus.CLOSED,
            stage=PipelineStage.CLOSED_WON,
            closed_at=timezone.now() + timedelta(days=6),
        )
        lost_deal = DealFactory(
            status=DealStatus.CLOSED,
            stage=PipelineStage.CLOSED_LOST,
            closed_at=timezone.now() + timedelta(days=4),
        )

        res = admin_client.get("/api/analytics/deals/")
        data = res.data["by_stage"]

        assert len(data) == 6
        assert data[0]["stage"] == PipelineStage.NEW_LEAD
        assert data[1]["stage"] == PipelineStage.QUALIFICATION
        assert data[2]["stage"] == PipelineStage.PROPOSAL_SENT
        assert data[3]["stage"] == PipelineStage.NEGOTIATION
        assert data[4]["stage"] == PipelineStage.CLOSED_WON
        assert data[5]["stage"] == PipelineStage.CLOSED_LOST

        assert data[0]["count"] == 1
        assert data[0]["on_hold"] == 0
        assert data[0]["total_amount"] == float(new_deal.amount)
        assert data[0]["conversion"] == 100

        assert data[1]["count"] == 1
        assert data[1]["on_hold"] == 0
        assert data[1]["total_amount"] == float(qualification_deal.amount)
        assert data[1]["conversion"] == 200

        assert data[2]["count"] == 2
        assert data[2]["on_hold"] == 1
        assert data[2]["total_amount"] == float(proposal_sent_deal.amount + on_hold_deal.amount)
        assert data[2]["conversion"] == 50

        assert data[3]["count"] == 1
        assert data[3]["on_hold"] == 0
        assert data[3]["total_amount"] == float(negotiation_deal.amount)
        assert data[3]["conversion"] == 100

        assert data[4]["count"] == 1
        assert data[4]["on_hold"] == 0
        assert data[4]["total_amount"] == float(won_deal.amount)
        assert data[4]["conversion"] is None

        assert data[5]["count"] == 1
        assert data[5]["on_hold"] == 0
        assert data[5]["total_amount"] == float(lost_deal.amount)
        assert data[5]["conversion"] is None


@pytest.mark.django_db
class TestAnalyticsDealsByPipelineEndpoint:
    # /api/analytics/deals/by-pipeline/
    # GET
    def test_admin_can_get_deals_by_pipeline_analytics(self, admin_client):
        DealFactory.create_batch(3)
        res = admin_client.get("/api/analytics/deals/by-pipeline/")
        assert res.status_code == 200

    def test_manager_can_get_deals_by_pipeline_analytics_only_for_own_team(self, manager_client, manager_user):
        team_user = UserFactory(team=manager_user.team)
        team_pipeline = PipelineFactory(assigned_to=team_user)
        team_deals = DealFactory.create_batch(3, pipeline=team_pipeline)

        DealFactory.create_batch(3)

        res = manager_client.get("/api/analytics/deals/by-pipeline/")
        assert res.status_code == 200
        assert len(res.data) == 1
        data = res.data[0]
        assert data["pipeline_name"] == team_pipeline.name
        assert data["analytics"]["total"] == 3

    def test_sales_rep_can_get_deals_by_pipeline_analytics_only_for_own_pipelines(self, sales_rep_client,
                                                                                  sales_rep_user):
        sales_rep_pipeline = PipelineFactory(assigned_to=sales_rep_user)
        sales_rep_deals = DealFactory.create_batch(3, pipeline=sales_rep_pipeline)

        DealFactory.create_batch(3)

        res = sales_rep_client.get("/api/analytics/deals/by-pipeline/")
        assert res.status_code == 200
        assert len(res.data) == 1
        data = res.data[0]
        assert data["pipeline_name"] == sales_rep_pipeline.name
        assert data["analytics"]["total"] == 3


@pytest.mark.django_db
class TestAnalyticsDealsByTeamEndpoint:
    # /api/analytics/deals/by-team/
    # GET
    def test_admin_can_get_deals_by_team_analytics(self, admin_client):
        DealFactory.create_batch(3)
        res = admin_client.get("/api/analytics/deals/by-team/")
        assert res.status_code == 200

    def test_manager_cannot_get_deals_by_team_analytics(self, manager_client):
        DealFactory.create_batch(3)

        res = manager_client.get("/api/analytics/deals/by-team/")

        assert res.status_code == 403

    def test_sales_rep_cannot_get_deals_by_team_analytics(self, sales_rep_client):
        DealFactory.create_batch(3)

        res = sales_rep_client.get("/api/analytics/deals/by-team/")

        assert res.status_code == 403
