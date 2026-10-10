import pytest

from crm_app.tests.factories import ContactFactory, DealFactory, ActivityFactory
from auth_app.tests.factories import UserFactory


@pytest.mark.django_db
class TestAnalyticsDashboardEndpoint:
    # /api/analytics/dashboard/
    # GET
    def test_admin_can_get_dashboard_analytics(self, admin_client):
        contacts = ContactFactory.create_batch(3)
        deals = DealFactory.create_batch(5, contact=contacts[0])
        ActivityFactory.create_batch(9, deal=deals[0])

        res = admin_client.get("/api/analytics/dashboard/")

        assert res.status_code == 200
        assert res.data["deals"]["total"] == 5
        assert res.data["contacts"]["total"] == 3
        assert res.data["activities"]["total"] == 9

    def test_manager_can_get_dashboard_analytics(self, manager_client, manager_user):
        team_user = UserFactory(team=manager_user.team)

        ContactFactory.create_batch(3)
        contacts = ContactFactory.create_batch(3, created_by=team_user)
        deals = DealFactory.create_batch(5, contact=contacts[0])
        DealFactory.create_batch(5, contact=contacts[0], assigned_to=team_user)
        ActivityFactory.create_batch(9, deal=deals[0])
        ActivityFactory.create_batch(9, deal=deals[0], assigned_to=team_user)

        res = manager_client.get("/api/analytics/dashboard/")

        assert res.status_code == 200
        assert res.data["deals"]["total"] == 5
        assert res.data["contacts"]["total"] == 3
        assert res.data["activities"]["total"] == 9

    def test_sales_rep_cannot_get_dashboard_analytics(self, sales_rep_client):
        res = sales_rep_client.get("/api/analytics/dashboard/")

        assert res.status_code == 403

    def test_employee_cannot_get_dashboard_analytics(self, employee_client):
        res = employee_client.get("/api/analytics/dashboard/")

        assert res.status_code == 403


@pytest.mark.django_db
class TestAnalyticsDashboardMyEndpoint:
    # /api/analytics/dashboard/my/
    # GET
    def test_admin_can_get_dashboard_my_analytics(self, admin_client, admin_user):
        contacts = ContactFactory.create_batch(3, created_by=admin_user)
        DealFactory.create_batch(5, contact=contacts[0], assigned_to=admin_user)
        deals = DealFactory.create_batch(5, contact=contacts[0])
        ActivityFactory.create_batch(9, deal=deals[0], assigned_to=admin_user)
        ActivityFactory.create_batch(9, deal=deals[0])

        res = admin_client.get("/api/analytics/dashboard/my/")

        assert res.status_code == 200
        assert res.data["deals"]["total"] == 5
        assert res.data["contacts"]["total"] == 3
        assert res.data["activities"]["total"] == 9

    def test_manager_can_get_dashboard_analytics(self, manager_client, manager_user):
        contacts = ContactFactory.create_batch(3, created_by=manager_user)
        DealFactory.create_batch(5, contact=contacts[0], assigned_to=manager_user)
        deals = DealFactory.create_batch(5, contact=contacts[0])
        ActivityFactory.create_batch(9, deal=deals[0], assigned_to=manager_user)
        ActivityFactory.create_batch(9, deal=deals[0])

        res = manager_client.get("/api/analytics/dashboard/my/")

        assert res.status_code == 200
        assert res.data["deals"]["total"] == 5
        assert res.data["contacts"]["total"] == 3
        assert res.data["activities"]["total"] == 9

    def test_sales_rep_can_get_dashboard_my_analytics(self, sales_rep_client, sales_rep_user):
        contacts = ContactFactory.create_batch(3, created_by=sales_rep_user)
        DealFactory.create_batch(5, contact=contacts[0], assigned_to=sales_rep_user)
        deals = DealFactory.create_batch(5, contact=contacts[0])
        ActivityFactory.create_batch(9, deal=deals[0], assigned_to=sales_rep_user)
        ActivityFactory.create_batch(9, deal=deals[0])

        res = sales_rep_client.get("/api/analytics/dashboard/my/")

        assert res.status_code == 200
        assert res.data["deals"]["total"] == 5
        assert res.data["contacts"]["total"] == 3
        assert res.data["activities"]["total"] == 9

    def test_employee_cannot_get_dashboard_my_analytics(self, employee_client):
        res = employee_client.get("/api/analytics/dashboard/my/")

        assert res.status_code == 403
