import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from .factories import ProductFactory, ActivityFactory, ActivityScriptFactory
from crm_app.models import PipelineStage, ActivityType, ActivityScript, Activity
from auth_app.tests.factories import UserFactory


@pytest.mark.django_db
class TestActivityScriptsEndpoint:
    # /api/activity-scripts/
    # GET
    def test_admin_can_list_activity_scripts(self, admin_client):
        ActivityScriptFactory.create_batch(3)
        res = admin_client.get("/api/activity-scripts/")
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_manager_can_list_activity_scripts(self, manager_client):
        ActivityScriptFactory.create_batch(3)
        res = manager_client.get("/api/activity-scripts/")
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_sales_rep_can_list_activity_scripts(self, sales_rep_client):
        ActivityScriptFactory.create_batch(3)
        res = sales_rep_client.get("/api/activity-scripts/")
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_employee_cannot_list_activity_scripts(self, employee_client):
        ActivityScriptFactory.create_batch(3)
        res = employee_client.get("/api/activity-scripts/")
        assert res.status_code == 403

    def test_list_response_fields(self, admin_client):
        activity_script = ActivityScriptFactory(attachment=SimpleUploadedFile(
            name="test.pdf",
            content=b"pdf content",
            content_type="application/pdf"
        ))
        res = admin_client.get("/api/activity-scripts/")

        activity_script_data = res.data[0]

        assert activity_script_data["id"] == str(activity_script.id)
        assert activity_script_data["title"] == activity_script.title
        assert activity_script_data["text"] == activity_script.text
        assert str(activity_script.attachment) in activity_script_data["attachment"]
        assert activity_script_data["activity_type"] == activity_script.activity_type
        assert activity_script_data["stage"] == activity_script.stage
        assert activity_script_data["product"] == activity_script.product.id
        assert activity_script_data["created_by"] == activity_script.created_by.id
        assert (list(str(activity_id) for activity_id in activity_script_data["activities"]) ==
                list(str(activity.id) for activity in activity_script.activities.all()))

    # POST
    def test_admin_can_create_activity_script(self, admin_client, admin_user):
        product = ProductFactory()
        data = {
            "title": "Test",
            "text": "test activity script",
            "attachment": SimpleUploadedFile(
                name="test.pdf",
                content=b"pdf content",
                content_type="application/pdf"),
            "activity_type": ActivityType.CALL,
            "stage": PipelineStage.NEW_LEAD,
            "product": product.id,
        }
        res = admin_client.post("/api/activity-scripts/", data=data, format="multipart")
        assert res.status_code == 201

        activity_script = ActivityScript.objects.get(id=res.data["id"])

        assert activity_script.title == data['title']
        assert activity_script.text == data['text']
        assert activity_script.attachment.name
        assert activity_script.attachment.name.startswith("attachments/test")
        assert activity_script.attachment.name.endswith(".pdf")
        assert activity_script.activity_type == data['activity_type']
        assert activity_script.stage == data['stage']
        assert activity_script.product == product
        assert activity_script.created_by == admin_user

    def test_manager_can_create_activity_script(self, manager_client, manager_user):
        product = ProductFactory()
        data = {
            "title": "Test",
            "text": "test activity script",
            "attachment": SimpleUploadedFile(
                name="test.pdf",
                content=b"pdf content",
                content_type="application/pdf"),
            "activity_type": ActivityType.CALL,
            "stage": PipelineStage.NEW_LEAD,
            "product": product.id,
        }
        res = manager_client.post("/api/activity-scripts/", data=data, format="multipart")
        assert res.status_code == 201

        activity_script = ActivityScript.objects.get(id=res.data["id"])

        assert activity_script.title == data['title']
        assert activity_script.text == data['text']
        assert activity_script.attachment.name
        assert activity_script.attachment.name.startswith("attachments/test")
        assert activity_script.attachment.name.endswith(".pdf")
        assert activity_script.activity_type == data['activity_type']
        assert activity_script.stage == data['stage']
        assert activity_script.product == product
        assert activity_script.created_by == manager_user

    def test_sales_rep_can_create_activity_script(self, sales_rep_user, sales_rep_client):
        product = ProductFactory()
        data = {
            "title": "Test",
            "text": "test activity script",
            "attachment": SimpleUploadedFile(
                name="test.pdf",
                content=b"pdf content",
                content_type="application/pdf"),
            "activity_type": ActivityType.CALL,
            "stage": PipelineStage.NEW_LEAD,
            "product": product.id,
        }
        res = sales_rep_client.post("/api/activity-scripts/", data=data, format="multipart")
        assert res.status_code == 201

        activity_script = ActivityScript.objects.get(id=res.data["id"])

        assert activity_script.title == data['title']
        assert activity_script.text == data['text']
        assert activity_script.attachment.name
        assert activity_script.attachment.name.startswith("attachments/test")
        assert activity_script.attachment.name.endswith(".pdf")
        assert activity_script.activity_type == data['activity_type']
        assert activity_script.stage == data['stage']
        assert activity_script.product == product
        assert activity_script.created_by == sales_rep_user

    def test_employee_cannot_create_activity_script(self, employee_client, employee_user):
        res = employee_client.post("/api/activity-scripts/", data={}, format="multipart")
        assert res.status_code == 403

    # /api/activity-scripts/{activity-script-id}/
    # retrieve
    def test_admin_can_retrieve_activity_script(self, admin_client):
        activity_script = ActivityScriptFactory()
        res = admin_client.get(f"/api/activity-scripts/{activity_script.id}/")
        assert res.status_code == 200

    def test_manager_can_retrieve_activity_script(self, manager_client):
        activity_script = ActivityScriptFactory()
        res = manager_client.get(f"/api/activity-scripts/{activity_script.id}/")
        assert res.status_code == 200

    def test_sales_rep_can_retrieve_activity_script(self, sales_rep_client):
        activity_script = ActivityScriptFactory()
        res = sales_rep_client.get(f"/api/activity-scripts/{activity_script.id}/")
        assert res.status_code == 200

    def test_employee_cannot_retrieve_activity_script(self, employee_client):
        activity_script = ActivityScriptFactory()
        res = employee_client.get(f"/api/activity-scripts/{activity_script.id}/")
        assert res.status_code == 403

    # partial_update
    def test_admin_can_update_activity_script(self, admin_client):
        new_product = ProductFactory()
        activity_script = ActivityScriptFactory()
        data = {
            "title": "Test",
            "text": "test activity script",
            "attachment": SimpleUploadedFile(
                name="test.pdf",
                content=b"pdf content",
                content_type="application/pdf"),
            "activity_type": ActivityType.MEETING,
            "stage": PipelineStage.QUALIFICATION,
            "product": new_product.id,
        }

        res = admin_client.patch(f"/api/activity-scripts/{activity_script.id}/", data=data, format="multipart")
        assert res.status_code == 200

        activity_script.refresh_from_db()
        assert activity_script.title == data['title']
        assert activity_script.text == data['text']
        assert activity_script.attachment.name
        assert activity_script.attachment.name.startswith("attachments/test")
        assert activity_script.attachment.name.endswith(".pdf")
        assert activity_script.activity_type == data['activity_type']
        assert activity_script.stage == data['stage']
        assert activity_script.product == new_product

    def test_manager_can_update_activity_script_created_by_team_member(self, manager_client, manager_user):
        new_product = ProductFactory()
        user = UserFactory(team=manager_user.team)
        activity_script = ActivityScriptFactory(created_by=user)
        data = {
            "title": "Test",
            "text": "test activity script",
            "attachment": SimpleUploadedFile(
                name="test.pdf",
                content=b"pdf content",
                content_type="application/pdf"),
            "activity_type": ActivityType.MEETING,
            "stage": PipelineStage.QUALIFICATION,
            "product": new_product.id,
        }

        res = manager_client.patch(f"/api/activity-scripts/{activity_script.id}/", data=data, format="multipart")
        assert res.status_code == 200

        activity_script.refresh_from_db()
        assert activity_script.title == data['title']
        assert activity_script.text == data['text']
        assert activity_script.attachment.name
        assert activity_script.attachment.name.startswith("attachments/test")
        assert activity_script.attachment.name.endswith(".pdf")
        assert activity_script.activity_type == data['activity_type']
        assert activity_script.stage == data['stage']
        assert activity_script.product == new_product

    def test_manager_cannot_update_activity_script_created_by_user_from_another_team(self, manager_client):
        activity_script = ActivityScriptFactory()
        res = manager_client.patch(f"/api/activity-scripts/{activity_script.id}/")
        assert res.status_code == 404

    def test_sales_rep_can_update_own_activity_script(self, sales_rep_client, sales_rep_user):
        new_product = ProductFactory()
        activity_script = ActivityScriptFactory(created_by=sales_rep_user)
        data = {
            "title": "Test",
            "text": "test activity script",
            "attachment": SimpleUploadedFile(
                name="test.pdf",
                content=b"pdf content",
                content_type="application/pdf"),
            "activity_type": ActivityType.MEETING,
            "stage": PipelineStage.QUALIFICATION,
            "product": new_product.id,
        }

        res = sales_rep_client.patch(f"/api/activity-scripts/{activity_script.id}/", data=data, format="multipart")
        assert res.status_code == 200

        activity_script.refresh_from_db()
        assert activity_script.title == data['title']
        assert activity_script.text == data['text']
        assert activity_script.attachment.name
        assert activity_script.attachment.name.startswith("attachments/test")
        assert activity_script.attachment.name.endswith(".pdf")
        assert activity_script.activity_type == data['activity_type']
        assert activity_script.stage == data['stage']
        assert activity_script.product == new_product

    def test_sales_rep_cannot_update_activity_script_created_by_other_users(self, sales_rep_client):
        activity_script = ActivityScriptFactory()
        res = sales_rep_client.patch(f"/api/activity-scripts/{activity_script.id}/")
        assert res.status_code == 404

    def test_read_only_fields_cannot_be_updated(self, admin_client):
        activity_script = ActivityScriptFactory()
        data = {
            'created_by': UserFactory().id,
            'activities': [ActivityFactory().id],
        }

        res = admin_client.patch(f"/api/activity-scripts/{activity_script.id}/", data=data, format="multipart")
        assert res.status_code == 200

        activity_script.refresh_from_db()
        assert activity_script.created_by != data["created_by"]
        assert (list(str(activity_id) for activity_id in data["activities"]) !=
                list(str(activity.id) for activity in activity_script.activities.all()))

    # delete
    def test_admin_can_delete_activity_script(self, admin_client):
        activity_script = ActivityScriptFactory()
        res = admin_client.delete(f"/api/activity-scripts/{activity_script.id}/")
        assert res.status_code == 204
        assert not ActivityScript.objects.filter(id=activity_script.id).exists()

    def test_manager_can_delete_activity_script_created_by_team_member(self, manager_client, manager_user):
        user = UserFactory(team=manager_user.team)
        activity_script = ActivityScriptFactory(created_by=user)

        res = manager_client.delete(f"/api/activity-scripts/{activity_script.id}/")
        assert res.status_code == 204
        assert not ActivityScript.objects.filter(id=activity_script.id).exists()

    def test_manager_cannot_delete_activity_script_created_by_user_from_another_team(self, manager_client):
        activity_script = ActivityScriptFactory()

        res = manager_client.delete(f"/api/activity-scripts/{activity_script.id}/")
        assert res.status_code == 404
        assert ActivityScript.objects.filter(id=activity_script.id).exists()

    def test_sales_rep_can_delete_own_activity_script(self, sales_rep_client, sales_rep_user):
        activity_script = ActivityScriptFactory(created_by=sales_rep_user)

        res = sales_rep_client.delete(f"/api/activity-scripts/{activity_script.id}/")
        assert res.status_code == 204
        assert not ActivityScript.objects.filter(id=activity_script.id).exists()

    def test_sales_rep_cannot_delete_activity_script_created_by_other_users(self, sales_rep_client):
        activity_script = ActivityScriptFactory()

        res = sales_rep_client.delete(f"/api/activity-scripts/{activity_script.id}/")
        assert res.status_code == 404
        assert ActivityScript.objects.filter(id=activity_script.id).exists()

    def test_employee_cannot_delete_activity_script(self, employee_client):
        activity_script = ActivityScriptFactory()

        res = employee_client.delete(f"/api/activity-scripts/{activity_script.id}/")
        assert res.status_code == 403
        assert ActivityScript.objects.filter(id=activity_script.id).exists()
