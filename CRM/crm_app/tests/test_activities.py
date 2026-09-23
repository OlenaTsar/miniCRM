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
class TestActivitiesEndpoint:
    # /api/activities/
    # GET
    def test_admin_can_list_activities(self, admin_client):
        ActivityFactory.create_batch(3)
        res = admin_client.get("/api/activities/")
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_manager_can_list_activities_assigned_to_team_member(self, manager_client, manager_user):
        user = UserFactory(team=manager_user.team)
        activity = ActivityFactory(assigned_to=user)

        res = manager_client.get("/api/activities/")

        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["id"] == str(activity.id)

    def test_manager_cannot_list_activities_assigned_to_user_from_another_team(self, manager_client):
        activity = ActivityFactory()
        res = manager_client.get("/api/activities/")
        assert res.status_code == 200
        assert len(res.data) == 0

    def test_sales_rep_can_list_own_activities(self, sales_rep_client, sales_rep_user):
        activity = ActivityFactory(assigned_to=sales_rep_user)

        res = sales_rep_client.get("/api/activities/")

        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["id"] == str(activity.id)

    def test_sales_rep_cannot_list_activities_assigned_to_another_user(self, sales_rep_client):
        activity = ActivityFactory()
        res = sales_rep_client.get("/api/activities/")
        assert res.status_code == 200
        assert len(res.data) == 0

    def test_employee_cannot_list_activities(self, employee_client):
        res = employee_client.get("/api/activities/")
        assert res.status_code == 403

    def test_list_response_fields(self, admin_client):
        activity = ActivityFactory()

        res = admin_client.get(f"/api/activities/")

        activity_data = res.data[0]
        assert activity_data["id"] == str(activity.id)
        assert activity_data["title"] == activity.title
        assert activity_data["description"] == activity.description
        assert activity_data["activity_type"] == activity.activity_type
        assert activity_data["outcome"] == activity.outcome
        assert parse_datetime(activity_data["created_at"]) == activity.created_at
        assert parse_datetime(activity_data["due_date"]) == activity.due_date
        assert activity_data["assigned_to"] == activity.assigned_to.id
        assert activity_data["deal"] == activity.deal.id
        assert activity_data["contact"] == activity.contact.id
        assert activity_data["script"] == activity.script.id
        assert activity_data["notification"] == activity.notification.id

    def test_list_activities_display_archived(self, admin_client):
        activities = ActivityFactory.create_batch(3)
        archive = ArchiveFactory()
        archived_activities = ActivityFactory.create_batch(3, archived=archive)

        # при звичайному запиті архівований вміст не повертається
        res = admin_client.get("/api/activities/")
        assert res.status_code == 200
        assert len(res.data) == 3
        activity_ids = [str(activity.id) for activity in activities]

        for activity_data in res.data:
            assert activity_data["id"] in activity_ids

        # при display_archived=true архівований вміст повертається
        res = admin_client.get("/api/activities/", query_params={"display_archived": "true"})
        assert res.status_code == 200
        assert len(res.data) == 6
        activity_ids.extend([str(activity.id) for activity in archived_activities])

        for activity_data in res.data:
            assert activity_data["id"] in activity_ids

    # POST
    def test_admin_can_create_activity(self, admin_client, admin_user):
        deal = DealFactory(assigned_to=admin_user)
        data = {
            "title": "Test",
            "activity_type": ActivityType.CALL,
            "due_date": timezone.now() + timedelta(days=1),
            "deal": deal.id,
        }
        res = admin_client.post("/api/activities/", data=data, format="json")
        assert res.status_code == 201

        activity = Activity.objects.get(id=res.data["id"])
        assert activity.title == data["title"]
        assert activity.activity_type == data["activity_type"]
        assert activity.due_date == data["due_date"]
        assert activity.deal == deal
        assert activity.assigned_to == admin_user

    def test_admin_can_create_activity_assigned_to_another_user(self, admin_client):
        user = UserFactory()
        deal = DealFactory(assigned_to=user)
        data = {
            "title": "Test",
            "activity_type": ActivityType.CALL,
            "due_date": timezone.now() + timedelta(days=1),
            "deal": deal.id,
            "assigned_to": user.id,
        }
        res = admin_client.post("/api/activities/", data=data, format="json")
        assert res.status_code == 201

        activity = Activity.objects.get(id=res.data["id"])
        assert activity.assigned_to == user

    def test_manager_can_create_activity_assigned_to_user_from_same_team(self, manager_client, manager_user):
        user = UserFactory(team=manager_user.team)
        deal = DealFactory(assigned_to=user)
        data = {
            "title": "Test",
            "activity_type": ActivityType.CALL,
            "due_date": timezone.now() + timedelta(days=1),
            "deal": deal.id,
            "assigned_to": user.id,
        }
        res = manager_client.post("/api/activities/", data=data, format="json")
        assert res.status_code == 201

        activity = Activity.objects.get(id=res.data["id"])
        assert activity.assigned_to == user

    def test_manager_cannot_create_activity_assigned_to_user_from_another_team(self, manager_client):
        user = UserFactory()
        deal = DealFactory(assigned_to=user)
        data = {
            "title": "Test",
            "activity_type": ActivityType.CALL,
            "due_date": timezone.now() + timedelta(days=1),
            "deal": deal.id,
            "assigned_to": user.id,
        }
        res = manager_client.post("/api/activities/", data=data, format="json")
        assert res.status_code == 403

    def test_sales_rep_can_create_activity(self, sales_rep_client, sales_rep_user):
        deal = DealFactory(assigned_to=sales_rep_user)
        data = {
            "title": "Test",
            "activity_type": ActivityType.CALL,
            "due_date": timezone.now() + timedelta(days=1),
            "deal": deal.id,
        }
        res = sales_rep_client.post("/api/activities/", data=data, format="json")
        assert res.status_code == 201

        activity = Activity.objects.get(id=res.data["id"])
        assert activity.assigned_to == sales_rep_user

    def test_sales_rep_cannot_create_activity_assigned_another_user(self, sales_rep_client):
        user = UserFactory()
        deal = DealFactory(assigned_to=user)
        data = {
            "title": "Test",
            "activity_type": ActivityType.CALL,
            "due_date": timezone.now() + timedelta(days=1),
            "deal": deal.id,
            "assigned_to": user.id,
        }
        res = sales_rep_client.post("/api/activities/", data=data, format="json")
        assert res.status_code == 400

    def test_create_activity_for_deal_assigned_to_different_user_fails(self, admin_client, admin_user):
        # помилка при спробі призначити активність користувачеві, якому не призначена відповідна угода

        # спроба створити активність для угоди іншого користувача, не вказавши в assigned_to цього користувача
        user = UserFactory()
        deal = DealFactory(assigned_to=user)
        data = {
            "title": "Test",
            "activity_type": ActivityType.CALL,
            "due_date": timezone.now() + timedelta(days=1),
            "deal": deal.id,
        }
        res = admin_client.post("/api/activities/", data=data, format="json")
        assert res.status_code == 400

        # спроба створити активність для своєї угоди, вказавши в assigned_to іншого користувача
        user = UserFactory()
        deal = DealFactory(assigned_to=admin_user)
        data = {
            "title": "Test",
            "activity_type": ActivityType.CALL,
            "due_date": timezone.now() + timedelta(days=1),
            "deal": deal.id,
            "assigned_to": user.id,
        }
        res = admin_client.post("/api/activities/", data=data, format="json")
        assert res.status_code == 400

    def test_activity_contact_is_set_automatically_from_deal(self, admin_client, admin_user):
        # поле contact заповнюється автоматично, відповідно до deal
        deal = DealFactory(assigned_to=admin_user)
        data = {
            "title": "Test",
            "activity_type": ActivityType.CALL,
            "due_date": timezone.now() + timedelta(days=1),
            "deal": deal.id,
        }
        res = admin_client.post("/api/activities/", data=data, format="json")
        assert res.data['contact'] == deal.contact.id

    def test_create_activity_with_invalid_due_date_fails(self, admin_client, admin_user):
        # due date має бути мінімум на 5 хвилин більше за час створення активності
        deal = DealFactory(assigned_to=admin_user)
        data = {
            "title": "Test",
            "activity_type": ActivityType.CALL,
            "due_date": timezone.now() + timedelta(minutes=4),
            "deal": deal.id,
        }
        res = admin_client.post("/api/activities/", data=data, format="json")
        assert res.status_code == 400

    def test_create_activity_automatically_creates_notification(self, admin_client, admin_user):
        # створення Notification при створенні Activity

        # Notification.notify_at повинно бути за годину до due_date
        # якщо до due_date залишилось менше години - notify_at через хвилину від поточного часу
        deal = DealFactory(assigned_to=admin_user)
        data1 = {
            "title": "Test",
            "activity_type": ActivityType.CALL,
            "due_date": timezone.now() + timedelta(days=1),
            "deal": deal.id,
        }
        data2 = {
            "title": "Test",
            "activity_type": ActivityType.CALL,
            "due_date": timezone.now() + timedelta(minutes=10),
            "deal": deal.id,
        }
        res1 = admin_client.post("/api/activities/", data=data1, format="json")
        res2 = admin_client.post("/api/activities/", data=data2, format="json")

        assert Notification.objects.filter(activity__id=res1.data['id']).exists()
        notify_at1 = Notification.objects.get(activity__id=res1.data['id']).notify_at
        assert notify_at1 == data1["due_date"] - timedelta(hours=1)

        assert Notification.objects.filter(activity__id=res2.data['id']).exists()
        notify_at2 = Notification.objects.get(activity__id=res2.data['id']).notify_at
        assert  timezone.now() <= notify_at2 <= timezone.now() + timedelta(minutes=1)

    # /api/activities/{activity-id}/
    # retrieve
    def test_admin_can_retrieve_activity(self, admin_client):
        activity = ActivityFactory()
        res = admin_client.get(f"/api/activities/{activity.id}/")
        assert res.status_code == 200

    def test_manager_can_retrieve_activity_assigned_to_user_from_same_team(self, manager_client, manager_user):
        user = UserFactory(team=manager_user.team)
        activity = ActivityFactory(assigned_to=user)
        res = manager_client.get(f"/api/activities/{activity.id}/")
        assert res.status_code == 200

    def test_manager_cannot_retrieve_activity_assigned_to_user_from_another_team(self, manager_client, manager_user):
        activity = ActivityFactory()
        res = manager_client.get(f"/api/activities/{activity.id}/")
        assert res.status_code == 404

    def test_sales_rep_can_retrieve_own_activity(self, sales_rep_client, sales_rep_user):
        activity = ActivityFactory(assigned_to=sales_rep_user)
        res = sales_rep_client.get(f"/api/activities/{activity.id}/")
        assert res.status_code == 200

    def test_sales_rep_cannot_retrieve_activity_assigned_to_another_user(self, sales_rep_client):
        activity = ActivityFactory()
        res = sales_rep_client.get(f"/api/activities/{activity.id}/")
        assert res.status_code == 404

    def test_retrieve_activity_display_archived(self, admin_client):
        archive = ArchiveFactory()
        archived_activity = ActivityFactory(archived=archive)

        # при звичайному запиті архівований вміст не повертається
        res = admin_client.get(f"/api/activities/{archived_activity.id}/")
        assert res.status_code == 404

        # при display_archived=true архівований вміст повертається
        res = admin_client.get(f"/api/activities/{archived_activity.id}/", query_params={"display_archived": "true"})
        assert res.status_code == 200

    # partial_update
    def test_admin_can_update_activity(self, admin_client):
        activity = ActivityFactory()
        new_data = {
            "title": "New title",
            "description": "New description",
            "outcome": 'test outcome',
            "due_date": timezone.now() + timedelta(days=10),
            "script": ActivityScriptFactory().id,
        }
        res = admin_client.patch(f"/api/activities/{activity.id}/", data=new_data, format="json")
        assert res.status_code == 200

        activity.refresh_from_db()
        assert new_data["title"] == activity.title
        assert new_data["description"] == activity.description
        assert new_data["outcome"] == activity.outcome
        assert new_data["due_date"] == activity.due_date
        assert new_data["script"] == activity.script.id

    def test_manager_can_update_activity_assigned_to_user_from_same_team(self, manager_client, manager_user):
        user = UserFactory(team=manager_user.team)
        activity = ActivityFactory(assigned_to=user)
        new_data = {
            "title": "New title",
            "description": "New description",
            "outcome": 'test outcome',
            "due_date": timezone.now() + timedelta(days=10),
            "script": ActivityScriptFactory().id,
        }
        res = manager_client.patch(f"/api/activities/{activity.id}/", data=new_data, format="json")
        assert res.status_code == 200

        activity.refresh_from_db()
        assert new_data["title"] == activity.title
        assert new_data["description"] == activity.description
        assert new_data["outcome"] == activity.outcome
        assert new_data["due_date"] == activity.due_date
        assert new_data["script"] == activity.script.id

    def test_manager_cannot_update_activity_assigned_to_user_from_another_team(self, manager_client):
        activity = ActivityFactory()
        res = manager_client.patch(f"/api/activities/{activity.id}/")
        assert res.status_code == 404

    def test_sales_rep_can_update_own_activity(self, sales_rep_client, sales_rep_user):
        activity = ActivityFactory(assigned_to=sales_rep_user)
        new_data = {
            "title": "New title",
            "description": "New description",
            "outcome": 'test outcome',
            "due_date": timezone.now() + timedelta(days=10),
            "script": ActivityScriptFactory().id,
        }
        res = sales_rep_client.patch(f"/api/activities/{activity.id}/", data=new_data, format="json")
        assert res.status_code == 200

        activity.refresh_from_db()
        assert new_data["title"] == activity.title
        assert new_data["description"] == activity.description
        assert new_data["outcome"] == activity.outcome
        assert new_data["due_date"] == activity.due_date
        assert new_data["script"] == activity.script.id

    def test_sales_rep_cannot_update_activity_assigned_to_another_user(self, sales_rep_client):
        activity = ActivityFactory()
        res = sales_rep_client.patch(f"/api/activities/{activity.id}/")
        assert res.status_code == 404

    def test_read_only_fields_cannot_be_updated(self, admin_client):
        activity = ActivityFactory()
        new_data = {
            "activity_type": ActivityType.EMAIL,
            "contact": ContactFactory().id,
            "created_at": timezone.now(),
            "completed_at": timezone.now(),
            "assigned_to": UserFactory().id,
            "deal": DealFactory().id,
            "notification": None,
        }
        res = admin_client.patch(f"/api/activities/{activity.id}/", data=new_data, format="json")
        assert res.status_code == 200

        activity.refresh_from_db()
        assert new_data["activity_type"] != activity.activity_type
        assert new_data["contact"] != activity.contact.id
        assert new_data["created_at"] != activity.created_at
        assert new_data["completed_at"] != activity.completed_at
        assert new_data["assigned_to"] != activity.assigned_to.id
        assert new_data["deal"] != activity.deal.id
        assert new_data["notification"] != activity.notification

    def test_change_any_fields_except_outcome_in_completed_activity_fails(self, admin_client):
        # зміна outcome
        activity = ActivityFactory(completed_at=timezone.now())
        new_data = {
            'outcome': "new outcome",
        }

        res = admin_client.patch(f"/api/activities/{activity.id}/", data=new_data, format="json")
        assert res.status_code == 200
        activity.refresh_from_db()
        assert activity.outcome == new_data["outcome"]

        # зміна будь-яких інших полів, окрім outcome
        activity = ActivityFactory(completed_at=timezone.now())
        new_data = {
            "title": "New title",
            "description": "New description",
            "due_date": timezone.now() + timedelta(days=10),
            "script": ActivityScriptFactory().id,
        }
        res = admin_client.patch(f"/api/activities/{activity.id}/", data=new_data, format="json")
        assert res.status_code == 400

    def test_change_activity_assignee_updates_notification_recipient(self, admin_client):
        # зміна Notification.recipient, якщо було змінено assigned_to в угоді, до якої належить активність
        # (змінити assigned_to активності можна лише через зміну assigned_to угоди)

        # також сповіщення повинне бути надіслано повторно новому отримувачу,
        # навіть якщо воно вже було надіслане минулому
        # (notify_at буде оновлено автоматично при зміні активності)

        deal = DealFactory()
        activity = ActivityFactory(deal=deal, assigned_to=deal.assigned_to)
        notification = activity.notification
        notification.sent_at = timezone.now()

        new_user = UserFactory()
        # потрібно створити для нового користувача Pipeline з тим самим продуктом, щоб угода перенеслась в неї
        PipelineFactory(product=deal.product, assigned_to=new_user)
        deal.assigned_to = new_user
        deal.save()

        notification.refresh_from_db()
        assert notification.recipient == new_user
        assert notification.sent_at is None

    def test_change_activity_due_date_updates_notification_notify_at(self, admin_client):
        # зміна Notification.notify_at при зміні Activity.due_date
        # notify_at повинно бути за годину до due_date
        # якщо до due_date залишилось менш ніж година - notify_at через хвилину від поточного часу
        # якщо сповіщення вже було надіслано - воно має бути надіслано повторно

        activity1 = ActivityFactory(due_date=timezone.now() + timedelta(hours=5))
        notification1 = activity1.notification

        activity2 = ActivityFactory(due_date=timezone.now() + timedelta(hours=5))
        notification2 = activity2.notification

        activity3 = ActivityFactory(due_date=timezone.now() + timedelta(minutes=50))
        notification3 = activity3.notification
        notification3.sent_at = timezone.now()
        notification3.read_at = timezone.now()
        notification3.save()

        # notify_at повинно бути за годину до due_date
        activity1.due_date = timezone.now() + timedelta(hours=3)
        activity1.save()
        notification1.refresh_from_db()
        assert notification1.notify_at == activity1.due_date - timedelta(hours=1)

        # якщо до due_date залишилось менш ніж година - notify_at через хвилину від поточного часу
        activity2.due_date = timezone.now() + timedelta(minutes=30)
        activity2.save()
        notification2.refresh_from_db()
        assert timezone.now() <= notification2.notify_at <= timezone.now() + timedelta(minutes=1)

        # якщо сповіщення вже було надіслано - воно має бути надіслано повторно
        activity3.due_date = timezone.now() + timedelta(hours=2)
        activity3.save()
        notification3.refresh_from_db()
        assert notification3.notify_at == activity3.due_date - timedelta(hours=1)
        assert notification3.sent_at is None
        assert notification3.read_at is None

    # delete
    def test_admin_can_delete_activity(self, admin_client):
        activity = ActivityFactory()
        res = admin_client.delete(f"/api/activities/{activity.id}/")
        assert res.status_code == 204
        assert not Activity.objects.filter(id=activity.id).exists()

    def test_manager_can_delete_activity_assigned_to_user_from_same_team(self, manager_client, manager_user):
        user = UserFactory(team=manager_user.team)
        activity = ActivityFactory(assigned_to=user)
        res = manager_client.delete(f"/api/activities/{activity.id}/")
        assert res.status_code == 204
        assert not Activity.objects.filter(id=activity.id).exists()

    def test_manager_cannot_delete_activity_assigned_to_user_from_another_team(self, manager_client):
        activity = ActivityFactory()
        res = manager_client.delete(f"/api/activities/{activity.id}/")
        assert res.status_code == 404
        assert Activity.objects.filter(id=activity.id).exists()

    def test_sales_rep_can_delete_own_activity(self, sales_rep_client, sales_rep_user):
        activity = ActivityFactory(assigned_to=sales_rep_user)
        res = sales_rep_client.delete(f"/api/activities/{activity.id}/")
        assert res.status_code == 204
        assert not Activity.objects.filter(id=activity.id).exists()

    def test_sales_rep_cannot_delete_activity_assigned_to_another_user(self, sales_rep_client):
        activity = ActivityFactory()
        res = sales_rep_client.delete(f"/api/activities/{activity.id}/")
        assert res.status_code == 404
        assert Activity.objects.filter(id=activity.id).exists()


@pytest.mark.django_db
class TestActivitiesMarkAsCompletedEndpoint:
    # /api/activities/{id}/mark-as-completed/
    # POST
    def test_admin_can_mark_activity_as_completed(self, admin_client):
        activity = ActivityFactory()
        res = admin_client.post(f"/api/activities/{activity.id}/mark-as-completed/")
        assert res.status_code == 204

        activity.refresh_from_db()
        assert activity.completed_at is not None

    def test_manager_can_mark_activity_assigned_to_user_from_same_team_as_completed(self, manager_client, manager_user):
        user = UserFactory(team=manager_user.team)
        activity = ActivityFactory(assigned_to=user)
        res = manager_client.post(f"/api/activities/{activity.id}/mark-as-completed/")
        assert res.status_code == 204

        activity.refresh_from_db()
        assert activity.completed_at is not None

    def test_manager_cannot_mark_activity_assigned_to_user_from_another_team_as_completed(self, manager_client):
        activity = ActivityFactory()
        res = manager_client.post(f"/api/activities/{activity.id}/mark-as-completed/")
        assert res.status_code == 404

    def test_sales_rep_can_mark_own_activity_as_completed(self, sales_rep_user, sales_rep_client):
        activity = ActivityFactory(assigned_to=sales_rep_user)
        res = sales_rep_client.post(f"/api/activities/{activity.id}/mark-as-completed/")
        assert res.status_code == 204

        activity.refresh_from_db()
        assert activity.completed_at is not None

    def test_sales_rep_cannot_mark_activity_assigned_to_another_user_as_completed(self, sales_rep_client):
        activity = ActivityFactory()
        res = sales_rep_client.post(f"/api/activities/{activity.id}/mark-as-completed/")
        assert res.status_code == 404

    def test_complete_activity_deletes_notification(self, admin_client):
        # видалення Notification для завершеної Activity
        activity = ActivityFactory()
        notification_id = activity.notification.id

        admin_client.post(f"/api/activities/{activity.id}/mark-as-completed/")

        assert not Notification.objects.filter(id=notification_id).exists()


@pytest.mark.django_db
class TestActivitiesActivityLogEndpoint:
    # /api/activities/{id}/activity-log/
    # GET
    def test_admin_can_retrieve_activity_log(self, admin_client):
        activity = ActivityFactory()
        res = admin_client.get(f"/api/activities/{activity.id}/activity-log/")
        assert res.status_code == 200

    def test_manager_can_retrieve_activity_log_assigned_to_user_from_same_team(self, manager_client, manager_user):
        user = UserFactory(team=manager_user.team)
        activity = ActivityFactory(assigned_to=user)
        res = manager_client.get(f"/api/activities/{activity.id}/activity-log/")
        assert res.status_code == 200

    def test_manager_cannot_retrieve_activity_log_assigned_to_user_from_another_team(self, manager_client):
        activity = ActivityFactory()
        res = manager_client.get(f"/api/activities/{activity.id}/activity-log/")
        assert res.status_code == 404

    def test_sales_rep_can_retrieve_own_activity_log(self, sales_rep_client, sales_rep_user):
        activity = ActivityFactory(assigned_to=sales_rep_user)
        res = sales_rep_client.get(f"/api/activities/{activity.id}/activity-log/")
        assert res.status_code == 200

    def test_sales_rep_cannot_retrieve_activity_log_assigned_to_another_user(self, sales_rep_client):
        activity = ActivityFactory()
        res = sales_rep_client.get(f"/api/activities/{activity.id}/activity-log/")
        assert res.status_code == 404

    def test_activity_log_response_fields(self, admin_client, admin_user):
        activity = ActivityFactory()

        admin_client.patch(f"/api/activities/{activity.id}/", data={"title": "New title"}, format="json")
        admin_client.post(f"/api/activities/{activity.id}/mark-as-completed/")

        res = admin_client.get(f"/api/activities/{activity.id}/activity-log/")

        assert len(res.data) == 3

        log_created = res.data[0]
        assert log_created["action"] == ActivityLog.Action.COMPLETED

        log_updated = res.data[1]
        assert log_updated["action"] == ActivityLog.Action.UPDATED

        log_completed = res.data[2]
        assert log_completed["action"] == ActivityLog.Action.CREATED
