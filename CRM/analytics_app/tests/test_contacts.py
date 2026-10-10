import pytest

from crm_app.tests.factories import ContactFactory, PipelineFactory, DealFactory
from auth_app.tests.factories import UserFactory


@pytest.mark.django_db
class TestAnalyticsContactsEndpoint:
    # /api/analytics/contacts/
    # GET
    def test_admin_can_get_contacts_analytics(self, admin_client):
        ContactFactory.create_batch(3)
        res = admin_client.get("/api/analytics/contacts/")
        assert res.status_code == 200

    def test_manager_can_get_analytics_only_for_own_team_contacts(self, manager_client, manager_user):
        # contacts, що додані користувачами не з команди менеджера
        ContactFactory.create_batch(3)
        res = manager_client.get("/api/analytics/contacts/")
        assert res.status_code == 200
        assert res.data["total"] == 0

        # contacts, що додані користувачами з команди менеджера
        user = UserFactory(team=manager_user.team)
        ContactFactory.create_batch(3, created_by=user)
        res = manager_client.get("/api/analytics/contacts/")
        assert res.status_code == 200
        assert res.data["total"] == 3

    def test_sales_rep_can_get_analytics_only_for_own_contacts(self, sales_rep_client, sales_rep_user):
        # contacts, що не належать sales_rep
        ContactFactory.create_batch(3)
        res = sales_rep_client.get("/api/analytics/contacts/")
        assert res.status_code == 200
        assert res.data["total"] == 0

        # contacts, що належать sales_rep
        ContactFactory.create_batch(3, created_by=sales_rep_user)
        res = sales_rep_client.get("/api/analytics/contacts/")
        assert res.status_code == 200
        assert res.data["total"] == 3

    def test_employee_cannot_get_contacts_analytics(self, employee_client):
        ContactFactory.create_batch(3)
        res = employee_client.get("/api/analytics/contacts/")
        assert res.status_code == 403


@pytest.mark.django_db
class TestAnalyticsContactsByPipelineEndpoint:
    # /api/analytics/contacts/by-pipeline/
    # GET
    def test_admin_can_get_contacts_by_pipeline_analytics(self, admin_client):
        ContactFactory.create_batch(3)
        res = admin_client.get("/api/analytics/contacts/by-pipeline/")
        assert res.status_code == 200

    def test_manager_can_get_contacts_by_pipeline_analytics_only_for_own_team(self, manager_client, manager_user):
        team_user = UserFactory(team=manager_user.team)
        team_pipeline = PipelineFactory(assigned_to=team_user)
        contact = ContactFactory()
        team_deal = DealFactory(pipeline=team_pipeline, contact=contact)

        ContactFactory.create_batch(3)

        res = manager_client.get("/api/analytics/contacts/by-pipeline/")
        assert res.status_code == 200
        assert len(res.data) == 1
        data = res.data[0]
        assert data["pipeline_name"] == team_pipeline.name
        assert data["analytics"]["total"] == 1

    def test_sales_rep_can_get_contacts_by_pipeline_analytics_only_for_own_pipelines(self, sales_rep_client,
                                                                                     sales_rep_user):
        sales_rep_pipeline = PipelineFactory(assigned_to=sales_rep_user)
        contact = ContactFactory()
        sales_rep_deal = DealFactory(pipeline=sales_rep_pipeline, contact=contact)

        ContactFactory.create_batch(3)

        res = sales_rep_client.get("/api/analytics/contacts/by-pipeline/")
        assert res.status_code == 200
        assert len(res.data) == 1
        data = res.data[0]
        assert data["pipeline_name"] == sales_rep_pipeline.name
        assert data["analytics"]["total"] == 1


@pytest.mark.django_db
class TestAnalyticsContactsByTeamEndpoint:
    # /api/analytics/contacts/by-team/
    # GET
    def test_admin_can_get_contacts_by_team_analytics(self, admin_client):
        ContactFactory.create_batch(3)
        res = admin_client.get("/api/analytics/contacts/by-team/")
        assert res.status_code == 200

    def test_manager_cannot_get_contacts_by_team_analytics(self, manager_client):
        ContactFactory.create_batch(3)

        res = manager_client.get("/api/analytics/contacts/by-team/")

        assert res.status_code == 403

    def test_sales_rep_cannot_get_contacts_by_team_analytics(self, sales_rep_client):
        ContactFactory.create_batch(3)

        res = sales_rep_client.get("/api/analytics/contacts/by-team/")

        assert res.status_code == 403
