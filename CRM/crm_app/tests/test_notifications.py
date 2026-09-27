from datetime import timedelta

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
class TestNotificationsEndpoint:
    # /api/notifications/
    # GET
    def test_admin_can_list_only_own_notifications(self, admin_client, admin_user):
        admin_activity = ActivityFactory(assigned_to=admin_user)
        admin_notification = admin_activity.notification
        another_user_activity = ActivityFactory()
        another_user_notification = another_user_activity.notification

        admin_notification.sent_at = timezone.now()
        admin_notification.save()
        another_user_notification.sent_at = timezone.now()
        another_user_notification.save()

        res = admin_client.get("/api/notifications/")
        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]['id'] == str(admin_notification.id)

    def test_manager_can_list_only_own_notifications(self, manager_client, manager_user):
        manager_activity = ActivityFactory(assigned_to=manager_user)
        manager_notification = manager_activity.notification
        another_user_activity = ActivityFactory()
        another_user_notification = another_user_activity.notification

        manager_notification.sent_at = timezone.now()
        manager_notification.save()
        another_user_notification.sent_at = timezone.now()
        another_user_notification.save()

        res = manager_client.get("/api/notifications/")
        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]['id'] == str(manager_notification.id)

    def test_sales_rep_can_list_only_own_notifications(self, sales_rep_client, sales_rep_user):
        sales_rep_activity = ActivityFactory(assigned_to=sales_rep_user)
        sales_rep_notification = sales_rep_activity.notification
        another_user_activity = ActivityFactory()
        another_user_notification = another_user_activity.notification

        sales_rep_notification.sent_at = timezone.now()
        sales_rep_notification.save()
        another_user_notification.sent_at = timezone.now()
        another_user_notification.save()

        res = sales_rep_client.get("/api/notifications/")
        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]['id'] == str(sales_rep_notification.id)

    def test_employee_cannot_list_notifications(self, employee_client):
        res = employee_client.get("/api/notifications/")
        assert res.status_code == 403

    def test_list_response_fields(self, admin_client, admin_user):
        admin_activity = ActivityFactory(assigned_to=admin_user)
        admin_notification = admin_activity.notification

        admin_notification.sent_at = timezone.now()
        admin_notification.save()

        res = admin_client.get("/api/notifications/")
        notification_data = res.data[0]

        assert notification_data['id'] == str(admin_notification.id)
        assert parse_datetime(notification_data['notify_at']) == admin_notification.notify_at
        assert parse_datetime(notification_data['sent_at']) == admin_notification.sent_at
        assert notification_data['read_at'] is None
        assert notification_data['recipient'] == admin_user.id
        assert notification_data['activity'] == admin_activity.id

    def test_list_notifications_returns_only_sent_notifications(self, admin_client, admin_user):
        # у запиті відображаються лише відправлені сповіщення
        activities = ActivityFactory.create_batch(2, assigned_to=admin_user)
        sent_notification = activities[0].notification

        sent_notification.sent_at = timezone.now()
        sent_notification.save()

        res = admin_client.get("/api/notifications/")

        assert len(res.data) == 1
        assert res.data[0]['id'] == str(sent_notification.id)

    # /api/notifications/
    # POST, PUT, PATCH
    def test_post_put_and_patch_methods_not_allowed(self, admin_client):
        res = admin_client.post("/api/notifications/")
        assert res.status_code == 405

        res = admin_client.put("/api/notifications/")
        assert res.status_code == 405

        res = admin_client.patch("/api/notifications/")
        assert res.status_code == 405

    # /api/notifications/{notification-id}/
    # retrieve
    def test_admin_can_retrieve_notification(self, admin_client, admin_user):
        activity = ActivityFactory(assigned_to=admin_user)
        notification = activity.notification

        notification.sent_at = timezone.now()
        notification.save()

        res = admin_client.get(f"/api/notifications/{notification.id}/")
        assert res.status_code == 200

    def test_manager_can_retrieve_notification(self, manager_client, manager_user):
        activity = ActivityFactory(assigned_to=manager_user)
        notification = activity.notification

        notification.sent_at = timezone.now()
        notification.save()

        res = manager_client.get(f"/api/notifications/{notification.id}/")
        assert res.status_code == 200

    def test_sales_rep_can_retrieve_notification(self, sales_rep_client, sales_rep_user):
        activity = ActivityFactory(assigned_to=sales_rep_user)
        notification = activity.notification

        notification.sent_at = timezone.now()
        notification.save()

        res = sales_rep_client.get(f"/api/notifications/{notification.id}/")
        assert res.status_code == 200

    # /api/notifications/
    # DELETE
    def test_admin_can_delete_notification(self, admin_client, admin_user):
        activity = ActivityFactory(assigned_to=admin_user)
        notification = activity.notification

        notification.sent_at = timezone.now()
        notification.save()

        res = admin_client.delete(f"/api/notifications/{notification.id}/")
        assert res.status_code == 204
        assert not Notification.objects.filter(id=notification.id).exists()

    def test_manager_can_delete_notification(self, manager_client, manager_user):
        activity = ActivityFactory(assigned_to=manager_user)
        notification = activity.notification

        notification.sent_at = timezone.now()
        notification.save()

        res = manager_client.delete(f"/api/notifications/{notification.id}/")
        assert res.status_code == 204
        assert not Notification.objects.filter(id=notification.id).exists()

    def test_sales_rep_can_delete_notification(self, sales_rep_client, sales_rep_user):
        activity = ActivityFactory(assigned_to=sales_rep_user)
        notification = activity.notification

        notification.sent_at = timezone.now()
        notification.save()

        res = sales_rep_client.delete(f"/api/notifications/{notification.id}/")
        assert res.status_code == 204
        assert not Notification.objects.filter(id=notification.id).exists()


@pytest.mark.django_db
class TestNotificationsMarkAsReadEndpoint:
    # /api/notifications/{id}/mark-as-read
    # POST
    def test_admin_can_mark_notification_as_read(self, admin_client, admin_user):
        activity = ActivityFactory(assigned_to=admin_user)
        notification = activity.notification

        notification.sent_at = timezone.now()
        notification.save()

        res = admin_client.post(f"/api/notifications/{notification.id}/mark-as-read/")
        assert res.status_code == 204

        notification.refresh_from_db()
        assert notification.read_at is not None

    def test_manager_can_mark_notification_as_read(self, manager_client, manager_user):
        activity = ActivityFactory(assigned_to=manager_user)
        notification = activity.notification

        notification.sent_at = timezone.now()
        notification.save()

        res = manager_client.post(f"/api/notifications/{notification.id}/mark-as-read/")
        assert res.status_code == 204

        notification.refresh_from_db()
        assert notification.read_at is not None

    def test_sales_rep_can_mark_notification_as_read(self, sales_rep_client, sales_rep_user):
        activity = ActivityFactory(assigned_to=sales_rep_user)
        notification = activity.notification

        notification.sent_at = timezone.now()
        notification.save()

        res = sales_rep_client.post(f"/api/notifications/{notification.id}/mark-as-read/")
        assert res.status_code == 204

        notification.refresh_from_db()
        assert notification.read_at is not None

    def test_mark_already_read_notification_as_read_fails(self, admin_client, admin_user):
        activity = ActivityFactory(assigned_to=admin_user)
        notification = activity.notification

        notification.sent_at = timezone.now()
        time_read = timezone.now()
        notification.read_at = time_read
        notification.save()

        res = admin_client.post(f"/api/notifications/{notification.id}/mark-as-read/")
        assert res.status_code == 204

        notification.refresh_from_db()
        assert notification.read_at == time_read

