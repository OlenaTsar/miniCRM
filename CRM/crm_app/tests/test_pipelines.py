import pytest
from django.utils.dateparse import parse_datetime

from .factories import PipelineFactory, ProductFactory, ArchiveFactory, DealFactory
from crm_app.models import Pipeline
from auth_app.tests.factories import UserFactory


@pytest.mark.django_db
class TestPipelinesEndpoint:
    # /api/pipelines/
    # GET
    def test_admin_can_list_pipelines(self, admin_client):
        PipelineFactory.create_batch(3)
        res = admin_client.get("/api/pipelines/")
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_manager_can_list_only_team_pipelines(self, manager_client, manager_user):
        # users з тієї самої команди
        team_users = UserFactory.create_batch(3, team=manager_user.team)
        # users з іншої команди
        other_users = UserFactory.create_batch(3)

        team_pipelines = []

        for user in team_users:
            team_pipelines.append(PipelineFactory(assigned_to=user))

        for user in other_users:
            PipelineFactory(assigned_to=user)

        res = manager_client.get("/api/pipelines/")
        assert res.status_code == 200
        assert len(res.data) == 3

        # список з id, які повинні повернутись
        pipeline_ids = [str(pipeline.id) for pipeline in team_pipelines]

        for pipeline_data in res.data:
            assert pipeline_data["id"] in pipeline_ids

    def test_sales_rep_can_list_only_own_pipelines(self, sales_rep_client, sales_rep_user):
        other_users = UserFactory.create_batch(3)

        sales_rep_pipelines = PipelineFactory.create_batch(2, assigned_to=sales_rep_user)

        for user in other_users:
            PipelineFactory(assigned_to=user)

        res = sales_rep_client.get("/api/pipelines/")
        assert res.status_code == 200
        assert len(res.data) == 2

        # список з id, які повинні повернутись
        pipeline_ids = [str(pipeline.id) for pipeline in sales_rep_pipelines]

        for pipeline_data in res.data:
            assert pipeline_data["id"] in pipeline_ids

    def test_employee_cannot_list_pipelines(self, employee_client):
        PipelineFactory.create_batch(3)
        res = employee_client.get("/api/pipelines/")
        assert res.status_code == 403

    def test_list_response_fields(self, admin_client):
        pipeline = PipelineFactory()
        res = admin_client.get(f"/api/pipelines/")

        pipeline_data = res.data[0]
        assert pipeline_data["id"] == str(pipeline.id)
        assert pipeline_data["name"] == pipeline.name
        assert parse_datetime(pipeline_data["created_at"]) == pipeline.created_at
        assert pipeline_data["assigned_to"] == pipeline.assigned_to.id
        assert pipeline_data["product"] == pipeline.product.id
        assert (list(str(deal_id) for deal_id in pipeline_data["deals"]) ==
                list(str(deal.id) for deal in pipeline.deals.all()))

    def test_list_pipelines_display_archived(self, admin_client):
        pipelines = PipelineFactory.create_batch(3)
        archive = ArchiveFactory()
        archived_pipelines = PipelineFactory.create_batch(3, archived=archive)

        # при звичайному запиті архівований вміст не повертається
        res = admin_client.get("/api/pipelines/")
        assert res.status_code == 200
        assert len(res.data) == 3
        pipeline_ids = [str(pipeline.id) for pipeline in pipelines]

        for pipeline_data in res.data:
            assert pipeline_data["id"] in pipeline_ids

        # при display_archived=true архівований вміст повертається
        res = admin_client.get("/api/pipelines/", query_params={"display_archived": "true"})
        assert res.status_code == 200
        assert len(res.data) == 6
        pipeline_ids.extend([str(pipeline.id) for pipeline in archived_pipelines])

        for pipeline_data in res.data:
            assert pipeline_data["id"] in pipeline_ids

    # POST
    def test_admin_can_create_pipelines(self, admin_client, admin_user):
        product = ProductFactory()
        res = admin_client.post("/api/pipelines/", data={"name": "Test", "product": product.id}, format="json")
        assert res.status_code == 201

        pipeline = Pipeline.objects.get(id=res.data["id"])
        assert pipeline.name == "Test"
        assert pipeline.assigned_to == admin_user

    def test_admin_can_create_pipelines_assigned_to_other_user(self, admin_client, admin_user):
        user = UserFactory()
        product = ProductFactory()
        data = {
            "name": "Test",
            "assigned_to": user.id,
            "product": product.id,
        }
        res = admin_client.post("/api/pipelines/", data=data, format="json")
        assert res.status_code == 201

        pipeline = Pipeline.objects.get(id=res.data["id"])
        assert pipeline.name == "Test"
        assert pipeline.assigned_to == user

    def test_manager_can_create_pipelines(self, manager_client, manager_user):
        product = ProductFactory()
        data = {
            "name": "Test",
            "product": product.id,
        }
        res = manager_client.post("/api/pipelines/", data=data, format="json")
        assert res.status_code == 201

        pipeline = Pipeline.objects.get(id=res.data["id"])
        assert pipeline.name == "Test"
        assert pipeline.assigned_to == manager_user

    def test_manager_can_create_pipelines_assigned_to_team_user(self, manager_client, manager_user):
        user = UserFactory(team=manager_user.team)
        product = ProductFactory()
        data = {
            "name": "Test",
            "assigned_to": user.id,
            "product": product.id,
        }
        res = manager_client.post("/api/pipelines/", data=data, format="json")
        assert res.status_code == 201

        pipeline = Pipeline.objects.get(id=res.data["id"])
        assert pipeline.name == "Test"
        assert pipeline.assigned_to == user

    def test_manager_cannot_create_pipelines_assigned_to_not_team_user(self, manager_client):
        user = UserFactory()
        product = ProductFactory()
        data = {
            "name": "Test",
            "assigned_to": user.id,
            "product": product.id,
        }
        res = manager_client.post("/api/pipelines/", data=data, format="json")
        assert res.status_code == 403

    def test_sales_rep_can_create_pipelines(self, sales_rep_client, sales_rep_user):
        product = ProductFactory()
        data = {
            "name": "Test",
            "product": product.id,
        }
        res = sales_rep_client.post("/api/pipelines/", data=data, format="json")
        assert res.status_code == 201

        pipeline = Pipeline.objects.get(id=res.data["id"])
        assert pipeline.name == "Test"
        assert pipeline.assigned_to == sales_rep_user

    def test_sales_rep_cannot_create_pipelines_assigned_to_other_user(self, sales_rep_client):
        user = UserFactory()
        product = ProductFactory()
        data = {
            "name": "Test",
            "assigned_to": user.id,
            "product": product.id,
        }
        res = sales_rep_client.post("/api/pipelines/", data=data, format="json")
        assert res.status_code == 403

    def test_employee_cannot_create_pipelines(self, employee_client):
        product = ProductFactory()
        data = {
            "name": "Test",
            "product": product.id,
        }
        res = employee_client.post("/api/pipelines/", data=data, format="json")
        assert res.status_code == 403

    def test_create_pipeline_without_required_fields_fails(self, admin_client):
        res = admin_client.post("/api/pipelines/")
        assert res.status_code == 400
        assert "name" in res.data

        res = admin_client.post("/api/pipelines/", data={"name": "test"}, format="json")
        assert res.status_code == 400
        assert "product" in res.data

    # /api/pipelines/{pipeline-id}/
    # retrieve
    def test_admin_can_retrieve_pipeline(self, admin_client):
        pipeline = PipelineFactory()
        res = admin_client.get(f"/api/pipelines/{pipeline.id}/")
        assert res.status_code == 200

    def test_manager_can_retrieve_team_pipeline(self, manager_client, manager_user):
        user = UserFactory(team=manager_user.team)
        pipeline = PipelineFactory(assigned_to=user)
        res = manager_client.get(f"/api/pipelines/{pipeline.id}/")
        assert res.status_code == 200

    def test_manager_cannot_retrieve_not_team_pipeline(self, manager_client):
        pipeline = PipelineFactory()
        res = manager_client.get(f"/api/pipelines/{pipeline.id}/")
        assert res.status_code == 404

    def test_sales_rep_can_retrieve_own_pipeline(self, sales_rep_client, sales_rep_user):
        pipeline = PipelineFactory(assigned_to=sales_rep_user)
        res = sales_rep_client.get(f"/api/pipelines/{pipeline.id}/")
        assert res.status_code == 200

    def test_sales_rep_cannot_retrieve_other_user_pipeline(self, sales_rep_client):
        pipeline = PipelineFactory()
        res = sales_rep_client.get(f"/api/pipelines/{pipeline.id}/")
        assert res.status_code == 404

    def test_retrieve_response_fields(self, admin_client):
        pipeline = PipelineFactory()
        res = admin_client.get(f"/api/pipelines/{pipeline.id}/")

        pipeline_data = res.data
        assert pipeline_data["id"] == str(pipeline.id)
        assert pipeline_data["name"] == pipeline.name
        assert parse_datetime(pipeline_data["created_at"]) == pipeline.created_at
        assert pipeline_data["assigned_to"] == pipeline.assigned_to.id
        assert pipeline_data["product"] == pipeline.product.id
        assert (list(str(deal_id) for deal_id in pipeline_data["deals"]) ==
                list(str(deal.id) for deal in pipeline.deals.all()))

    # partial_update
    def test_admin_can_update_pipeline(self, admin_client):
        user = UserFactory()
        pipeline = PipelineFactory()
        new_data = {
            "name": "New Name",
            'assigned_to': user.id,
        }
        res = admin_client.patch(f"/api/pipelines/{pipeline.id}/", data=new_data, format="json")
        assert res.status_code == 200

        pipeline.refresh_from_db()
        assert pipeline.name == new_data["name"]
        assert pipeline.assigned_to.id == new_data["assigned_to"]

    def test_manager_can_update_team_pipeline(self, manager_client, manager_user):
        user_1 = UserFactory(team=manager_user.team)
        user_2 = UserFactory(team=manager_user.team)
        pipeline = PipelineFactory(assigned_to=user_1)
        new_data = {
            "name": "New Name",
            'assigned_to': user_2.id,
        }
        res = manager_client.patch(f"/api/pipelines/{pipeline.id}/", data=new_data, format="json")
        assert res.status_code == 200

        pipeline.refresh_from_db()
        assert pipeline.name == new_data["name"]
        assert pipeline.assigned_to.id == new_data["assigned_to"]

    def test_manager_cannot_update_not_team_pipeline(self, manager_client):
        pipeline = PipelineFactory()
        res = manager_client.patch(f"/api/pipelines/{pipeline.id}/")
        assert res.status_code == 404

    def test_manager_cannot_change_assigned_to_not_team_user(self, manager_client, manager_user):
        team_user = UserFactory(team=manager_user.team)
        not_team_user = UserFactory()
        pipeline = PipelineFactory(assigned_to=team_user)

        res = manager_client.patch(
            f"/api/pipelines/{pipeline.id}/",
            data={"assigned_to": not_team_user.id},
            format="json"
        )
        assert res.status_code == 403

    def test_sales_rep_can_update_own_pipeline(self, sales_rep_client, sales_rep_user):
        pipeline = PipelineFactory(assigned_to=sales_rep_user)
        new_data = {
            "name": "New Name",
        }
        res = sales_rep_client.patch(f"/api/pipelines/{pipeline.id}/", data=new_data, format="json")
        assert res.status_code == 200

        pipeline.refresh_from_db()
        assert pipeline.name == new_data["name"]

    def test_sales_rep_cannot_update_pipeline_assigned_to_other_user(self, sales_rep_client):
        pipeline = PipelineFactory()
        res = sales_rep_client.patch(f"/api/pipelines/{pipeline.id}/")
        assert res.status_code == 404

    def test_sales_rep_cannot_change_assignee(self, sales_rep_client, sales_rep_user):
        pipeline = PipelineFactory(assigned_to=sales_rep_user)
        user = UserFactory()
        new_data = {
            "assigned_to": user.id,
        }
        res = sales_rep_client.patch(f"/api/pipelines/{pipeline.id}/", data=new_data, format="json")
        assert res.status_code == 403

    def test_employee_cannot_update_pipeline(self, employee_client):
        pipeline = PipelineFactory()
        res = employee_client.patch(f"/api/pipelines/{pipeline.id}/")
        assert res.status_code == 403

    def test_field_product_is_read_only(self, admin_client):
        product_1 = ProductFactory()
        product_2 = ProductFactory()
        pipeline = PipelineFactory(product=product_1)
        new_data = {
            "product": product_2.id,
        }
        res = admin_client.patch(f"/api/pipelines/{pipeline.id}/", data=new_data, format="json")

        assert res.status_code == 200

        pipeline.refresh_from_db()
        assert pipeline.product.id == product_1.id

    def test_change_pipeline_assignee_cascades_to_deals(self, admin_client):
        # перевіряє, що зміна assigned_to в pipeline поширюється на deals, які належать цьому pipeline
        pipeline = PipelineFactory()
        deals = DealFactory.create_batch(4, pipeline=pipeline)
        user = UserFactory()
        new_data = {
            "assigned_to": user.id,
        }

        res = admin_client.patch(f"/api/pipelines/{pipeline.id}/", data=new_data, format="json")

        assert res.status_code == 200

        pipeline.refresh_from_db()
        assert pipeline.assigned_to == user

        for deal in deals:
            deal.refresh_from_db()
            assert deal.assigned_to == user

    # delete
    def test_admin_can_delete_pipeline(self, admin_client):
        pipeline = PipelineFactory()
        res = admin_client.delete(f"/api/pipelines/{pipeline.id}/")
        assert res.status_code == 204
        assert not Pipeline.objects.filter(id=pipeline.id).exists()

    def test_manager_can_delete_team_pipeline(self, manager_client, manager_user):
        user = UserFactory(team=manager_user.team)
        pipeline = PipelineFactory(assigned_to=user)
        res = manager_client.delete(f"/api/pipelines/{pipeline.id}/")

        assert res.status_code == 204
        assert not Pipeline.objects.filter(id=pipeline.id).exists()

    def test_manager_cannot_delete_not_team_pipeline(self, manager_client, manager_user):
        pipeline = PipelineFactory()
        res = manager_client.delete(f"/api/pipelines/{pipeline.id}/")

        assert res.status_code == 404
        assert Pipeline.objects.filter(id=pipeline.id).exists()

    def test_sales_rep_can_delete_own_pipeline(self, sales_rep_client, sales_rep_user):
        pipeline = PipelineFactory(assigned_to=sales_rep_user)
        res = sales_rep_client.delete(f"/api/pipelines/{pipeline.id}/")

        assert res.status_code == 204
        assert not Pipeline.objects.filter(id=pipeline.id).exists()

    def test_sales_rep_cannot_delete_not_own_pipeline(self, sales_rep_client):
        pipeline = PipelineFactory()
        res = sales_rep_client.delete(f"/api/pipelines/{pipeline.id}/")

        assert res.status_code == 404
        assert Pipeline.objects.filter(id=pipeline.id).exists()

    def test_employee_cannot_delete_pipeline(self, employee_client):
        pipeline = PipelineFactory()
        res = employee_client.delete(f"/api/pipelines/{pipeline.id}/")
        assert res.status_code == 403
