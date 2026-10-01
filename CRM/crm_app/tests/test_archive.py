from datetime import timedelta

import pytest
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .factories import (PipelineFactory,
                        ContactFactory,
                        ArchiveFactory,
                        DealFactory,
                        ActivityFactory,
                        ProductFactory)
from crm_app.models import PipelineStage, DealStatus, Activity, Deal, Notification, Archive, ArchivingType
from auth_app.tests.factories import UserFactory, TeamFactory


@pytest.mark.django_db
class TestArchiveEndpoint:
    # /api/archive/
    # GET
    def test_admin_can_list_archives(self, admin_client):
        ArchiveFactory.create_batch(3)
        res = admin_client.get("/api/archive/")
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_manager_can_list_only_archives_assigned_to_team_member(self, manager_client, manager_user):
        # manager може бачити тільки ті архівації, які стосуються даних користувачів своєї команди
        # при цьому йому повинні відображатись deals/activities/pipelines лише користувачів його команди
        ArchiveFactory.create_batch(3)
        user = UserFactory(team=manager_user.team)
        archive = ArchiveFactory()
        DealFactory.create_batch(3, archived=archive)
        deal = DealFactory(assigned_to=user, archived=archive)

        res = manager_client.get("/api/archive/")

        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["id"] == str(archive.id)
        assert deal.id in res.data[0]["deals"]

    def test_manager_can_list_empty_archive_archived_by_team_user(self, manager_client, manager_user):
        user = UserFactory(team=manager_user.team)
        archive = ArchiveFactory(archived_by=user)

        res = manager_client.get("/api/archive/")

        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["id"] == str(archive.id)

    def test_sales_rep_can_list_only_own_archives(self, sales_rep_client, sales_rep_user):
        # sales_rep може бачити тільки ті архівації, які стосуються його даних
        # при цьому йому повинні відображатись лише його deals/activities/pipelines
        ArchiveFactory.create_batch(3)
        archive = ArchiveFactory()
        DealFactory.create_batch(3, archived=archive)
        deal = DealFactory(assigned_to=sales_rep_user, archived=archive)

        res = sales_rep_client.get("/api/archive/")

        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["id"] == str(archive.id)
        assert deal.id in res.data[0]["deals"]

    def test_sales_rep_can_list_empty_archive_archived_by_self(self, sales_rep_client, sales_rep_user):
        archive = ArchiveFactory(archived_by=sales_rep_user)

        res = sales_rep_client.get("/api/archive/")

        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["id"] == str(archive.id)

    def test_employee_cannot_list_archives(self, employee_client):
        res = employee_client.get("/api/archive/")
        assert res.status_code == 403

    def test_list_response_fields(self, admin_client):
        archive = ArchiveFactory()
        pipelines = PipelineFactory.create_batch(3, archived=archive)
        deals = DealFactory.create_batch(3, archived=archive)
        activities = ActivityFactory.create_batch(3, archived=archive)

        res = admin_client.get("/api/archive/")

        data = res.data[0]

        assert len(res.data) == 1
        assert data["id"] == str(archive.id)
        assert data["archiving_type"] == archive.archiving_type
        assert parse_datetime(data["timestamp"]) == archive.timestamp
        assert data["archived_by"] == archive.archived_by.id
        assert (list(str(pipeline_id) for pipeline_id in data["pipelines"]) ==
                list(str(pipeline.id) for pipeline in pipelines))
        assert (list(str(deal_id) for deal_id in data["deals"]) ==
                list(str(deal.id) for deal in deals))
        assert (list(str(activity_id) for activity_id in data["activities"]) ==
                list(str(activity.id) for activity in activities))

    # retrieve
    def test_admin_can_retrieve_archive(self, admin_client):
        archive = ArchiveFactory()
        res = admin_client.get(f"/api/archive/{archive.id}/")
        assert res.status_code == 200

    def test_manager_can_retrieve_archive_assigned_to_user_from_same_team(self, manager_client, manager_user):
        # manager може бачити тільки ті архівації, які стосуються даних користувачів своєї команди
        user = UserFactory(team=manager_user.team)
        archive = ArchiveFactory()
        DealFactory(assigned_to=user, archived=archive)

        res = manager_client.get(f"/api/archive/{archive.id}/")
        assert res.status_code == 200

    def test_manager_cannot_retrieve_archive_assigned_to_user_from_another_team(self, manager_client):
        archive = ArchiveFactory()
        DealFactory(archived=archive)
        res = manager_client.get(f"/api/archive/{archive.id}/")
        assert res.status_code == 404

    def test_sales_rep_can_retrieve_own_archive(self, sales_rep_client, sales_rep_user):
        archive = ArchiveFactory()
        DealFactory(assigned_to=sales_rep_user, archived=archive)
        res = sales_rep_client.get(f"/api/archive/{archive.id}/")
        assert res.status_code == 200

    def test_sales_rep_cannot_retrieve_archive_assigned_to_another_user(self, sales_rep_client):
        archive = ArchiveFactory()
        DealFactory(archived=archive)
        res = sales_rep_client.get(f"/api/archive/{archive.id}/")
        assert res.status_code == 404

    # PUT, PATCH
    def test_post_put_and_patch_methods_not_allowed(self, admin_client):

        res = admin_client.put("/api/archive/")
        assert res.status_code == 405

        res = admin_client.patch("/api/archive/")
        assert res.status_code == 405

    # POST
    def test_admin_can_create_archive(self, admin_client, admin_user):
        deal = DealFactory()
        data = {
            "deals": [deal.id]
        }
        res = admin_client.post("/api/archive/", data=data, format="json")
        assert res.status_code == 201

        archive = Archive.objects.get(id=res.data["id"])
        assert archive.archiving_type == ArchivingType.MANUAL
        assert archive.archived_by == admin_user
        assert list(archive.deals.all()) == [deal]

    def test_manager_can_create_archive_with_team_data(self, manager_client, manager_user):
        # manager може створити архів додавши туди дані своєї команди
        user = UserFactory(team=manager_user.team)
        pipeline = PipelineFactory(assigned_to=user)
        deal = DealFactory(assigned_to=user)
        activity = ActivityFactory(assigned_to=user)
        data = {
            "pipelines": [pipeline.id],
            "deals": [deal.id],
            "activities": [activity.id],
        }
        res = manager_client.post("/api/archive/", data=data, format="json")
        assert res.status_code == 201

        archive = Archive.objects.get(id=res.data["id"])
        assert archive.archiving_type == ArchivingType.MANUAL
        assert archive.archived_by == manager_user
        assert list(archive.pipelines.all()) == [pipeline]
        assert list(archive.deals.all()) == [deal]
        assert list(archive.activities.all()) == [activity]

    def test_manager_cannot_create_archive_with_not_team_data(self, manager_client, manager_user):
        # manager не може створити архів з даними чужої команди
        # тобто, архів повинен створитися, але дані, які належать користувачам іншої команди,
        # не повинні бути заархівованими
        pipeline = PipelineFactory()
        deal = DealFactory()
        activity = ActivityFactory()
        data = {
            "pipelines": [pipeline.id],
            "deals": [deal.id],
            "activities": [activity.id],
        }
        res = manager_client.post("/api/archive/", data=data, format="json")
        assert res.status_code == 201

        archive = Archive.objects.get(id=res.data["id"])
        assert archive.archiving_type == ArchivingType.MANUAL
        assert archive.archived_by == manager_user
        assert list(archive.pipelines.all()) == []
        assert list(archive.deals.all()) == []
        assert list(archive.activities.all()) == []

    def test_sales_rep_can_create_archive_with_own_data(self, sales_rep_client, sales_rep_user):
        # sales_rep може створити архів додавши туди свої дані
        pipeline = PipelineFactory(assigned_to=sales_rep_user)
        deal = DealFactory(assigned_to=sales_rep_user)
        activity = ActivityFactory(assigned_to=sales_rep_user)
        data = {
            "pipelines": [pipeline.id],
            "deals": [deal.id],
            "activities": [activity.id],
        }
        res = sales_rep_client.post("/api/archive/", data=data, format="json")
        assert res.status_code == 201

        archive = Archive.objects.get(id=res.data["id"])
        assert archive.archiving_type == ArchivingType.MANUAL
        assert archive.archived_by == sales_rep_user
        assert list(archive.pipelines.all()) == [pipeline]
        assert list(archive.deals.all()) == [deal]
        assert list(archive.activities.all()) == [activity]

    def test_sales_rep_cannot_create_archive_with_another_user_data(self, sales_rep_client, sales_rep_user):
        # sales_rep не може заархівувати дані інших користувачів
        pipeline = PipelineFactory()
        deal = DealFactory()
        activity = ActivityFactory()
        data = {
            "pipelines": [pipeline.id],
            "deals": [deal.id],
            "activities": [activity.id],
        }
        res = sales_rep_client.post("/api/archive/", data=data, format="json")
        assert res.status_code == 201

        archive = Archive.objects.get(id=res.data["id"])
        assert archive.archiving_type == ArchivingType.MANUAL
        assert archive.archived_by == sales_rep_user
        assert list(archive.pipelines.all()) == []
        assert list(archive.deals.all()) == []
        assert list(archive.activities.all()) == []

    def test_already_archived_data_is_not_archived_again(self, admin_client):
        # дані, які вже є в іншому архіві, не архівуються повторно
        # тобто, новий архів створюється, але заархівовані раніше дані в нього не додаються
        deal = DealFactory(archived=ArchiveFactory())

        res = admin_client.post("/api/archive/", data={"deals": [deal.id]}, format="json")
        assert res.status_code == 201

        new_archive = Archive.objects.get(id=res.data["id"])
        assert deal.archived != new_archive
        assert list(new_archive.deals.all()) == []

    # DELETE
    def test_admin_can_delete_archive(self, admin_client):
        archive = ArchiveFactory()
        res = admin_client.delete(f"/api/archive/{archive.id}/")
        assert res.status_code == 204
        assert not Archive.objects.filter(id=archive.id).exists()

    def test_manager_can_delete_archive_archived_by_user_from_same_team(self, manager_client, manager_user):
        user = UserFactory(team=manager_user.team)
        archive = ArchiveFactory(archived_by=user)
        res = manager_client.delete(f"/api/archive/{archive.id}/")
        assert res.status_code == 204
        assert not Archive.objects.filter(id=archive.id).exists()

    def test_manager_can_delete_archive_with_team_users_data(self, manager_client, manager_user):
        # manager може видалити архів, який містить виключно дані користувачів команди менеджера
        archive = ArchiveFactory(archiving_type=ArchivingType.PERIODIC, archived_by=None)
        user = UserFactory(team=manager_user.team)
        deal = DealFactory(assigned_to=user, archived=archive)

        res = manager_client.delete(f"/api/archive/{archive.id}/")

        assert res.status_code == 204
        assert not Archive.objects.filter(id=archive.id).exists()
        deal.refresh_from_db()
        assert deal.archived is None

    def test_manager_cannot_delete_archive_archived_by_user_from_another_team(self, manager_client, manager_user):
        archive = ArchiveFactory()
        res = manager_client.delete(f"/api/archive/{archive.id}/")
        assert res.status_code == 404
        assert Archive.objects.filter(id=archive.id).exists()

    def test_manager_cannot_delete_archive_with_data_of_another_user(self, manager_client, manager_user):
        # manager не може видалити архів, якщо в ньому є дані користувачів з іншої команди
        archive = ArchiveFactory(archiving_type=ArchivingType.PERIODIC, archived_by=None)
        team_user = UserFactory(team=manager_user.team)
        manager_deal = DealFactory(assigned_to=team_user, archived=archive)
        another_team_user_deal = DealFactory(archived=archive)

        res = manager_client.delete(f"/api/archive/{archive.id}/")

        assert res.status_code == 403
        assert Archive.objects.filter(id=archive.id).exists()

    def test_sales_rep_can_delete_own_archive(self, sales_rep_client, sales_rep_user):
        archive = ArchiveFactory(archived_by=sales_rep_user)
        res = sales_rep_client.delete(f"/api/archive/{archive.id}/")
        assert res.status_code == 204
        assert not Archive.objects.filter(id=archive.id).exists()

    def test_sales_rep_can_delete_archive_with_only_own_data(self, sales_rep_client, sales_rep_user):
        archive = ArchiveFactory(archiving_type=ArchivingType.PERIODIC, archived_by=None)
        deal = DealFactory(assigned_to=sales_rep_user, archived=archive)

        res = sales_rep_client.delete(f"/api/archive/{archive.id}/")

        assert res.status_code == 204
        assert not Archive.objects.filter(id=archive.id).exists()
        deal.refresh_from_db()
        assert deal.archived is None

    def test_sales_rep_cannot_delete_archive_archived_by_another_user(self, sales_rep_client):
        archive = ArchiveFactory()
        res = sales_rep_client.delete(f"/api/archive/{archive.id}/")
        assert res.status_code == 404
        assert Archive.objects.filter(id=archive.id).exists()

    def test_sales_rep_cannot_delete_archive_with_data_of_another_user(self, sales_rep_client, sales_rep_user):
        archive = ArchiveFactory(archiving_type=ArchivingType.PERIODIC, archived_by=None)
        sales_rep_deal = DealFactory(assigned_to=sales_rep_user, archived=archive)
        another_user_deal = DealFactory(archived=archive)

        res = sales_rep_client.delete(f"/api/archive/{archive.id}/")

        assert res.status_code == 403
        assert Archive.objects.filter(id=archive.id).exists()

    def test_deleting_archive_unarchives_archived_data(self, admin_client):
        # дані, які є в архіві, розархівовуються, коли архів видаляється
        archive = ArchiveFactory()
        pipeline = PipelineFactory(archived=archive)
        deal = DealFactory(archived=archive)
        activity = ActivityFactory()
        activity.archived = archive
        activity.save()  # потрібно архівовувати activity таким чином, щоб видалялось notification при архівації

        res = admin_client.delete(f"/api/archive/{archive.id}/")

        pipeline.refresh_from_db()
        deal.refresh_from_db()
        activity.refresh_from_db()

        assert pipeline.archived is None
        assert deal.archived is None
        assert activity.archived is None


@pytest.mark.django_db
class TestUnarchiveEndpoint:
    # /api/archive/unarchive/
    # POST
    def test_admin_can_unarchive_data(self, admin_client):
        archive = ArchiveFactory()
        pipeline = PipelineFactory(archived=archive)
        deal = DealFactory(archived=archive)
        activity = ActivityFactory()
        activity.archived = archive
        activity.save()

        data = {
            "pipelines": [pipeline.id],
            "deals": [deal.id],
            "activities": [activity.id],
        }

        res = admin_client.post("/api/archive/unarchive/", data=data, format="json")

        assert res.status_code == 204

        pipeline.refresh_from_db()
        deal.refresh_from_db()
        activity.refresh_from_db()

        assert pipeline.archived is None
        assert deal.archived is None
        assert activity.archived is None

    def test_manager_can_unarchive_data_assigned_to_team_member(self, manager_client, manager_user):
        archive = ArchiveFactory()
        user = UserFactory(team=manager_user.team)
        pipeline = PipelineFactory(archived=archive, assigned_to=user)
        deal = DealFactory(archived=archive, assigned_to=user)
        activity = ActivityFactory(assigned_to=user)
        activity.archived = archive
        activity.save()

        data = {
            "pipelines": [pipeline.id],
            "deals": [deal.id],
            "activities": [activity.id],
        }

        res = manager_client.post("/api/archive/unarchive/", data=data, format="json")

        assert res.status_code == 204

        pipeline.refresh_from_db()
        deal.refresh_from_db()
        activity.refresh_from_db()

        assert pipeline.archived is None
        assert deal.archived is None
        assert activity.archived is None

    def test_manager_cannot_unarchive_data_assigned_to_user_from_another_team(self, manager_client):
        archive = ArchiveFactory()
        pipeline = PipelineFactory(archived=archive)
        deal = DealFactory(archived=archive)
        activity = ActivityFactory()
        activity.archived = archive
        activity.save()

        data = {
            "pipelines": [pipeline.id],
            "deals": [deal.id],
            "activities": [activity.id],
        }

        res = manager_client.post("/api/archive/unarchive/", data=data, format="json")

        assert res.status_code == 204

        pipeline.refresh_from_db()
        deal.refresh_from_db()
        activity.refresh_from_db()

        assert pipeline.archived == archive
        assert deal.archived == archive
        assert activity.archived == archive

    def test_sales_rep_can_unarchive_own_data(self, sales_rep_client, sales_rep_user):
        archive = ArchiveFactory()
        pipeline = PipelineFactory(archived=archive, assigned_to=sales_rep_user)
        deal = DealFactory(archived=archive, assigned_to=sales_rep_user)
        activity = ActivityFactory(assigned_to=sales_rep_user)
        activity.archived = archive
        activity.save()

        data = {
            "pipelines": [pipeline.id],
            "deals": [deal.id],
            "activities": [activity.id],
        }

        res = sales_rep_client.post("/api/archive/unarchive/", data=data, format="json")

        assert res.status_code == 204

        pipeline.refresh_from_db()
        deal.refresh_from_db()
        activity.refresh_from_db()

        assert pipeline.archived is None
        assert deal.archived is None
        assert activity.archived is None

    def test_sales_rep_cannot_unarchive_data_assigned_to_another_user(self, sales_rep_client):
        archive = ArchiveFactory()
        pipeline = PipelineFactory(archived=archive)
        deal = DealFactory(archived=archive)
        activity = ActivityFactory()
        activity.archived = archive
        activity.save()

        data = {
            "pipelines": [pipeline.id],
            "deals": [deal.id],
            "activities": [activity.id],
        }

        res = sales_rep_client.post("/api/archive/unarchive/", data=data, format="json")

        assert res.status_code == 204

        pipeline.refresh_from_db()
        deal.refresh_from_db()
        activity.refresh_from_db()

        assert pipeline.archived == archive
        assert deal.archived == archive
        assert activity.archived == archive


@pytest.mark.django_db
class TestArchiveSignals:
    def test_archiving_pipeline_archives_related_deals(self, admin_client):
        pipeline = PipelineFactory()
        deals = DealFactory.create_batch(3, pipeline=pipeline)

        res = admin_client.post("/api/archive/", data={"pipelines": [pipeline.id]}, format="json")

        pipeline.refresh_from_db()
        archive = pipeline.archived

        for deal in deals:
            deal.refresh_from_db()
            assert deal.archived == archive

    def test_unarchiving_pipeline_unarchives_related_deals(self, admin_client):
        archive = ArchiveFactory()
        pipeline = PipelineFactory(archived=archive)
        deals = DealFactory.create_batch(3, pipeline=pipeline, archived=archive)

        res = admin_client.post("/api/archive/unarchive/", data={"pipelines": [pipeline.id]}, format="json")

        for deal in deals:
            deal.refresh_from_db()
            assert deal.archived is None

    def test_archiving_deal_archives_related_activities(self, admin_client):
        deal = DealFactory()
        activities = ActivityFactory.create_batch(3, deal=deal)

        res = admin_client.post("/api/archive/", data={"deals": [deal.id]}, format="json")

        deal.refresh_from_db()
        archive = deal.archived

        for activity in activities:
            activity.refresh_from_db()
            assert activity.archived == archive

    def test_unarchiving_deal_unarchives_related_activities(self, admin_client):
        archive = ArchiveFactory()
        deal = DealFactory(archived=archive)
        activities = ActivityFactory.create_batch(3, deal=deal)
        for activity in activities:
            activity.archived = archive
            activity.save()

        res = admin_client.post("/api/archive/unarchive/", data={"deals": [deal.id]}, format="json")

        for activity in activities:
            activity.refresh_from_db()
            assert activity.archived is None

    def test_archiving_activity_deletes_notification(self, admin_client):
        activity = ActivityFactory()
        notification_id = activity.notification.id

        admin_client.post("/api/archive/", data={"activities": [activity.id]}, format="json")

        assert not Notification.objects.filter(id=notification_id).exists()

    def test_unarchiving_activity_restores_notification_if_activity_is_incomplete_and_not_overdue(self, admin_client):
        # створення нового Notification при деархівації Activity,
        # якщо активність не завершена і не є простроченою
        archive = ArchiveFactory()
        activity = ActivityFactory()
        activity.archived = archive
        activity.save()

        admin_client.post("/api/archive/unarchive/", data={"activities": [activity.id]}, format="json")

        activity.refresh_from_db()
        assert activity.notification is not None

    def test_unarchiving_activity_not_restores_notification_if_activity_is_complete_or_overdue(self, admin_client):
        # новий Notification не створюється при деархівації Activity,
        # якщо активність є завершена або є простроченою
        archive = ArchiveFactory()
        complete_activity = ActivityFactory(completed_at=timezone.now())
        overdue_activity = ActivityFactory(due_date=timezone.now() - timedelta(hours=1))
        complete_activity.archived = archive
        complete_activity.save()
        overdue_activity.archived = archive
        overdue_activity.save()

        data = {
            "activities": [complete_activity.id, overdue_activity.id]
        }

        admin_client.post("/api/archive/unarchive/", data=data, format="json")

        complete_activity.refresh_from_db()
        overdue_activity.refresh_from_db()
        assert not Notification.objects.filter(activity=complete_activity).exists()
        assert not Notification.objects.filter(activity=overdue_activity).exists()

    def test_deleting_product_archives_related_data(self):
        product = ProductFactory()
        pipeline = PipelineFactory(product=product)
        deal = DealFactory(product=product, pipeline=pipeline)
        activity = ActivityFactory(deal=deal)

        product.delete()

        pipeline.refresh_from_db()
        deal.refresh_from_db()
        activity.refresh_from_db()

        assert pipeline.archived is not None
        assert deal.archived is not None
        assert activity.archived is not None
        assert pipeline.archived == deal.archived == activity.archived
        assert pipeline.archived.archiving_type == ArchivingType.PRODUCT_DELETED

    def test_deleting_user_archives_related_data(self):
        user = UserFactory()
        pipeline = PipelineFactory(assigned_to=user)
        deal = DealFactory(assigned_to=user, pipeline=pipeline)
        activity = ActivityFactory(assigned_to=user)

        user.delete()

        pipeline.refresh_from_db()
        deal.refresh_from_db()
        activity.refresh_from_db()

        assert pipeline.archived is not None
        assert deal.archived is not None
        assert activity.archived is not None
        assert pipeline.archived == deal.archived == activity.archived
        assert pipeline.archived.archiving_type == ArchivingType.USER_DELETED

    def test_deleting_team_archives_related_data(self):
        team = TeamFactory()
        user = UserFactory(team=team)
        pipeline = PipelineFactory(assigned_to=user)
        deal = DealFactory(assigned_to=user, pipeline=pipeline)
        activity = ActivityFactory(assigned_to=user)

        team.delete()

        pipeline.refresh_from_db()
        deal.refresh_from_db()
        activity.refresh_from_db()

        assert pipeline.archived is not None
        assert deal.archived is not None
        assert activity.archived is not None
        assert pipeline.archived == deal.archived == activity.archived
        assert pipeline.archived.archiving_type == ArchivingType.TEAM_DELETED

    def test_removing_user_from_team_archives_related_data(self, admin_client):
        team = TeamFactory()
        user = UserFactory(team=team)
        pipeline = PipelineFactory(assigned_to=user)
        deal = DealFactory(assigned_to=user, pipeline=pipeline)
        activity = ActivityFactory(assigned_to=user)

        admin_client.post(f"/api/teams/{team.id}/remove-user/", data={"user": user.id}, format="json")

        pipeline.refresh_from_db()
        deal.refresh_from_db()
        activity.refresh_from_db()

        assert pipeline.archived is not None
        assert deal.archived is not None
        assert activity.archived is not None
        assert pipeline.archived == deal.archived == activity.archived
        assert pipeline.archived.archiving_type == ArchivingType.USER_REMOVED_FROM_TEAM

    def test_removing_product_from_team_archives_related_data(self, admin_client):
        product = ProductFactory()
        team = TeamFactory()
        team.products.set([product])
        user = UserFactory(team=team)
        pipeline = PipelineFactory(assigned_to=user, product=product)
        deal = DealFactory(assigned_to=user, pipeline=pipeline, product=product)
        activity = ActivityFactory(assigned_to=user, deal=deal)

        admin_client.post(f"/api/teams/{team.id}/remove-product/", data={"product": product.id}, format="json")

        pipeline.refresh_from_db()
        deal.refresh_from_db()
        activity.refresh_from_db()

        assert pipeline.archived is not None
        assert deal.archived is not None
        assert activity.archived is not None
        assert pipeline.archived == deal.archived == activity.archived
        assert pipeline.archived.archiving_type == ArchivingType.PRODUCT_REMOVED_FROM_TEAM
