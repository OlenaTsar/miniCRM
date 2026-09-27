from datetime import timedelta
from io import BytesIO
from openpyxl import load_workbook

import pytest
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .factories import (PipelineFactory,
                        ContactFactory,
                        ArchiveFactory,
                        DealFactory,
                        ActivityFactory,
                        ActivityScriptFactory)
from crm_app.models import PipelineStage, DealStatus, Activity, ActivityType, Deal, Notification, ActivityLog
from auth_app.tests.factories import UserFactory


@pytest.mark.django_db
class TestReportsContactEndpoint:
    # /api/reports/contacts/
    # GET
    def test_admin_can_export_contacts_as_csv(self, admin_client):
        contact = ContactFactory()
        DealFactory.create_batch(3, contact=contact)

        res = admin_client.get("/api/reports/contacts/")

        assert res.status_code == 200
        assert res["Content-Type"] == "text/csv"
        assert 'attachment; filename="contacts_report_' in res["Content-Disposition"]

    def test_manager_can_export_contacts_as_csv(self, manager_client):
        contact = ContactFactory()
        DealFactory.create_batch(3, contact=contact)

        res = manager_client.get("/api/reports/contacts/")

        assert res.status_code == 200
        assert res["Content-Type"] == "text/csv"
        assert 'attachment; filename="contacts_report_' in res["Content-Disposition"]

    def test_sales_rep_can_export_contacts_as_csv(self, sales_rep_client):
        contact = ContactFactory()
        DealFactory.create_batch(3, contact=contact)

        res = sales_rep_client.get("/api/reports/contacts/")

        assert res.status_code == 200
        assert res["Content-Type"] == "text/csv"
        assert 'attachment; filename="contacts_report_' in res["Content-Disposition"]

    def test_employee_cannot_export_contacts(self, employee_client):
        res = employee_client.get("/api/reports/contacts/")

        assert res.status_code == 403

    def test_export_contacts_as_csv_response_fields(self, admin_client):
        contact = ContactFactory()
        DealFactory.create_batch(3, contact=contact)

        res = admin_client.get("/api/reports/contacts/")

        assert res.status_code == 200
        assert res["Content-Type"] == "text/csv"
        assert 'attachment; filename="contacts_report_' in res["Content-Disposition"]

        content = res.content.decode("utf-8")

        assert contact.first_name in content
        assert contact.last_name in content
        assert contact.email in content
        assert contact.phone in content
        assert contact.city in content
        assert contact.company.name in content
        assert contact.instagram_url in content
        assert contact.facebook_url in content
        assert contact.status in content
        assert "\n".join(contact.deals.values_list("name", flat=True)) in content
        assert str(contact.deals.count()) in content
        assert str(contact.activities.count()) in content
        assert contact.lead_source in content
        assert contact.created_by.email in content

    def test_admin_can_export_contacts_as_excel(self, admin_client):
        contact = ContactFactory()
        DealFactory.create_batch(3, contact=contact)

        res = admin_client.get("/api/reports/contacts/", {"file_format": "excel"})

        assert res.status_code == 200
        assert (
                res["Content-Type"]
                == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert 'attachment; filename="contacts_report_' in res["Content-Disposition"]

    def test_manager_can_export_contacts_as_excel(self, manager_client):
        contact = ContactFactory()
        DealFactory.create_batch(3, contact=contact)

        res = manager_client.get("/api/reports/contacts/", {"file_format": "excel"})

        assert res.status_code == 200
        assert (
                res["Content-Type"]
                == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert 'attachment; filename="contacts_report_' in res["Content-Disposition"]

    def test_sales_rep_can_export_contacts_as_excel(self, sales_rep_client):
        contact = ContactFactory()
        DealFactory.create_batch(3, contact=contact)

        res = sales_rep_client.get("/api/reports/contacts/", {"file_format": "excel"})

        assert res.status_code == 200
        assert (
                res["Content-Type"]
                == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert 'attachment; filename="contacts_report_' in res["Content-Disposition"]

    def test_export_contacts_as_excel_response_fields(self, admin_client):
        contact = ContactFactory()
        DealFactory.create_batch(3, contact=contact)

        res = admin_client.get("/api/reports/contacts/", {"file_format": "excel"})

        assert res.status_code == 200
        assert (
                res["Content-Type"]
                == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert 'attachment; filename="contacts_report_' in res["Content-Disposition"]

        workbook = load_workbook(BytesIO(res.content))
        worksheet = workbook.active

        values = list(worksheet.values)
        values_data = [value for row in values for value in row]

        assert contact.first_name in values_data
        assert contact.last_name in values_data
        assert contact.email in values_data
        assert contact.phone in values_data
        assert contact.city in values_data
        assert contact.company.name in values_data
        assert contact.instagram_url in values_data
        assert contact.facebook_url in values_data
        assert contact.status in values_data
        assert "\n".join(contact.deals.values_list("name", flat=True)) in values_data
        assert contact.deals.count() in values_data
        assert contact.activities.count() in values_data
        assert contact.lead_source in values_data
        assert contact.created_by.email in values_data


@pytest.mark.django_db
class TestReportsDealsEndpoint:
    # /api/reports/deals/
    # GET
    def test_admin_can_export_deals(self, admin_client):
        DealFactory.create_batch(3)

        # csv
        res = admin_client.get("/api/reports/deals/")

        assert res.status_code == 200
        assert res["Content-Type"] == "text/csv"
        assert 'attachment; filename="deals_report_' in res["Content-Disposition"]

        # excel
        res = admin_client.get("/api/reports/deals/", {"file_format": "excel"})

        assert res.status_code == 200
        assert (
                res["Content-Type"]
                == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert 'attachment; filename="deals_report_' in res["Content-Disposition"]

    def test_manager_can_export_deals_only_assigned_to_users_from_same_team(self, manager_client, manager_user):
        DealFactory.create_batch(3)
        user = UserFactory(team=manager_user.team)
        team_deal = DealFactory(assigned_to=user)

        # csv
        res = manager_client.get("/api/reports/deals/")

        content = res.content.decode("utf-8")

        assert res.status_code == 200
        assert res["Content-Type"] == "text/csv"
        assert 'attachment; filename="deals_report_' in res["Content-Disposition"]

        assert len(content.splitlines()) == 2  # один рядок заголовка + одна угода
        assert team_deal.name in content

        # excel
        res = manager_client.get("/api/reports/deals/", {"file_format": "excel"})

        assert res.status_code == 200
        assert (
                res["Content-Type"]
                == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert 'attachment; filename="deals_report_' in res["Content-Disposition"]

        workbook = load_workbook(BytesIO(res.content))
        worksheet = workbook.active

        values = list(worksheet.values)
        values_data = [value for row in values for value in row]

        assert worksheet.max_row == 2  # один рядок заголовка + одна угода
        assert team_deal.name in values_data

    def test_sales_rep_can_export_only_own_deals(self, sales_rep_client, sales_rep_user):
        DealFactory.create_batch(3)
        sales_rep_deal = DealFactory(assigned_to=sales_rep_user)

        # csv
        res = sales_rep_client.get("/api/reports/deals/")

        content = res.content.decode("utf-8")

        assert res.status_code == 200
        assert res["Content-Type"] == "text/csv"
        assert 'attachment; filename="deals_report_' in res["Content-Disposition"]

        assert len(content.splitlines()) == 2  # один рядок заголовка + одна угода
        assert sales_rep_deal.name in content

        # excel
        res = sales_rep_client.get("/api/reports/deals/", {"file_format": "excel"})

        assert res.status_code == 200
        assert (
                res["Content-Type"]
                == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert 'attachment; filename="deals_report_' in res["Content-Disposition"]

        workbook = load_workbook(BytesIO(res.content))
        worksheet = workbook.active

        values = list(worksheet.values)
        values_data = [value for row in values for value in row]

        assert worksheet.max_row == 2  # один рядок заголовка + одна угода
        assert sales_rep_deal.name in values_data

    def test_employee_cannot_export_deals(self, employee_client):
        res = employee_client.get("/api/reports/deals/")

        assert res.status_code == 403

    def test_export_deals_as_csv_response_fields(self, admin_client):
        deal = DealFactory(expected_close_date=timezone.now() + timedelta(days=3),
                           closed_at=timezone.now())

        res = admin_client.get("/api/reports/deals/")

        content = res.content.decode("utf-8")

        assert deal.name in content
        assert deal.description in content
        assert deal.status in content
        assert deal.stage in content
        assert str(deal.amount) in content
        assert deal.currency in content
        assert str(deal.expected_close_date)[:19] in content
        assert str(deal.created_at)[:19] in content
        assert str(deal.closed_at)[:19] in content
        assert deal.pipeline.name in content
        assert deal.product.name in content
        assert f"{deal.contact.first_name} {deal.contact.last_name}" in content
        assert deal.assigned_to.email in content

    def test_export_deals_as_excel_response_fields(self, admin_client):
        deal = DealFactory(expected_close_date=timezone.now() + timedelta(days=3),
                           closed_at=timezone.now())

        res = admin_client.get("/api/reports/deals/", {"file_format": "excel"})

        workbook = load_workbook(BytesIO(res.content))
        worksheet = workbook.active

        values = list(worksheet.values)
        values_data = [value for row in values for value in row]

        assert deal.name in values_data
        assert deal.description in values_data
        assert deal.status in values_data
        assert deal.stage in values_data
        assert str(deal.amount) in values_data
        assert deal.currency in values_data
        assert str(deal.expected_close_date)[:19] in values_data
        assert str(deal.created_at)[:19] in values_data
        assert str(deal.closed_at)[:19] in values_data
        assert deal.pipeline.name in values_data
        assert deal.product.name in values_data
        assert f"{deal.contact.first_name} {deal.contact.last_name}" in values_data
        assert deal.assigned_to.email in values_data


@pytest.mark.django_db
class TestReportsActivitiesEndpoint:
    # /api/reports/activities/
    # GET
    def test_admin_can_export_activities(self, admin_client):
        ActivityFactory.create_batch(3)

        # csv
        res = admin_client.get("/api/reports/activities/")

        assert res.status_code == 200
        assert res["Content-Type"] == "text/csv"
        assert 'attachment; filename="activities_report_' in res["Content-Disposition"]

        # excel
        res = admin_client.get("/api/reports/activities/", {"file_format": "excel"})

        assert res.status_code == 200
        assert (
                res["Content-Type"]
                == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert 'attachment; filename="activities_report_' in res["Content-Disposition"]

    def test_manager_can_export_activities_only_assigned_to_users_from_same_team(self, manager_client, manager_user):
        ActivityFactory.create_batch(3)
        user = UserFactory(team=manager_user.team)
        team_activity = ActivityFactory(assigned_to=user)

        # csv
        res = manager_client.get("/api/reports/activities/")

        content = res.content.decode("utf-8")

        assert res.status_code == 200
        assert res["Content-Type"] == "text/csv"
        assert 'attachment; filename="activities_report_' in res["Content-Disposition"]

        assert len(content.splitlines()) == 2  # один рядок заголовка + одна угода
        assert team_activity.title in content

        # excel
        res = manager_client.get("/api/reports/activities/", {"file_format": "excel"})

        assert res.status_code == 200
        assert (
                res["Content-Type"]
                == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert 'attachment; filename="activities_report_' in res["Content-Disposition"]

        workbook = load_workbook(BytesIO(res.content))
        worksheet = workbook.active

        values = list(worksheet.values)
        values_data = [value for row in values for value in row]

        assert worksheet.max_row == 2  # один рядок заголовка + одна угода
        assert team_activity.title in values_data

    def test_sales_rep_can_export_only_own_activities(self, sales_rep_client, sales_rep_user):
        ActivityFactory.create_batch(3)
        sales_rep_activity = ActivityFactory(assigned_to=sales_rep_user)

        # csv
        res = sales_rep_client.get("/api/reports/activities/")

        content = res.content.decode("utf-8")

        assert res.status_code == 200
        assert res["Content-Type"] == "text/csv"
        assert 'attachment; filename="activities_report_' in res["Content-Disposition"]

        assert len(content.splitlines()) == 2  # один рядок заголовка + одна угода
        assert sales_rep_activity.title in content

        # excel
        res = sales_rep_client.get("/api/reports/activities/", {"file_format": "excel"})

        assert res.status_code == 200
        assert (
                res["Content-Type"]
                == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert 'attachment; filename="activities_report_' in res["Content-Disposition"]

        workbook = load_workbook(BytesIO(res.content))
        worksheet = workbook.active

        values = list(worksheet.values)
        values_data = [value for row in values for value in row]

        assert worksheet.max_row == 2  # один рядок заголовка + одна угода
        assert sales_rep_activity.title in values_data

    def test_employee_cannot_export_activities(self, employee_client):
        res = employee_client.get("/api/reports/activities/")

        assert res.status_code == 403

    def test_export_activities_as_csv_response_fields(self, admin_client):
        activity = ActivityFactory(outcome="activity outcome",
                                   completed_at=timezone.now())

        res = admin_client.get("/api/reports/activities/")

        content = res.content.decode("utf-8")

        assert activity.title in content
        assert activity.description in content
        assert activity.activity_type in content
        assert f"{activity.contact.first_name} {activity.contact.last_name}" in content
        assert activity.deal.name in content
        assert activity.outcome in content
        assert str(activity.created_at)[:19] in content
        assert str(activity.due_date)[:19] in content
        assert str(activity.completed_at)[:19] in content
        assert activity.assigned_to.email in content

    def test_export_activities_as_excel_response_fields(self, admin_client):
        activity = ActivityFactory(outcome="activity outcome",
                                   completed_at=timezone.now())

        res = admin_client.get("/api/reports/activities/", {"file_format": "excel"})

        workbook = load_workbook(BytesIO(res.content))
        worksheet = workbook.active

        values = list(worksheet.values)
        values_data = [value for row in values for value in row]

        assert activity.title in values_data
        assert activity.description in values_data
        assert activity.activity_type in values_data
        assert f"{activity.contact.first_name} {activity.contact.last_name}" in values_data
        assert activity.deal.name in values_data
        assert activity.outcome in values_data
        assert str(activity.created_at)[:19] in values_data
        assert str(activity.due_date)[:19] in values_data
        assert str(activity.completed_at)[:19] in values_data
        assert activity.assigned_to.email in values_data
