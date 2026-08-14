import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io

from auth_app.tests.factories import UserFactory
from auth_app.models import User
from django.utils.dateparse import parse_datetime
from crm_app.tests.factories import (
    PipelineFactory,
    DealFactory,
    ActivityFactory,
)
from crm_app.models import ArchivingType


def create_test_image():
    img = Image.new("RGB", (100, 100), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    buffer.seek(0)
    return SimpleUploadedFile("avatar.jpg", buffer.read(), content_type="image/jpeg")


@pytest.mark.django_db
class TestUsersEndpointPermissions:
    # тестує тільки доступ

    # /api/users/
    def test_admin_can_list_users(self, admin_client):
        res = admin_client.get("/api/users/")
        assert res.status_code == 200

    def test_manager_can_list_users(self, manager_client):
        res = manager_client.get("/api/users/")
        assert res.status_code == 200

    def test_sales_rep_cannot_list_users(self, sales_rep_client):
        res = sales_rep_client.get("/api/users/")
        assert res.status_code == 403

    def test_employee_cannot_list_users(self, employee_client):
        res = employee_client.get("/api/users/")
        assert res.status_code == 403

    def test_unauthenticated_cannot_access(self, api_client):
        res = api_client.get("/api/users/")
        assert res.status_code == 401

    # /api/users/{user-id}/
    # retrieve
    def test_admin_can_retrieve_user(self, admin_client):
        user = UserFactory()
        res = admin_client.get(f"/api/users/{user.id}/")
        assert res.status_code == 200

    def test_manager_can_retrieve_user(self, manager_client, manager_user):
        # manager може отримати доступ до даних користувача зі своєї team
        user = UserFactory(team=manager_user.team)
        res = manager_client.get(f"/api/users/{user.id}/")
        assert res.status_code == 200

        # manager не може отримати доступ до даних користувача не зі своєї team
        user = UserFactory()
        res = manager_client.get(f"/api/users/{user.id}/")
        assert res.status_code == 404

    def test_sales_rep_cannot_retrieve_user(self, sales_rep_client):
        user = UserFactory()
        res = sales_rep_client.get(f"/api/users/{user.id}/")
        assert res.status_code == 403

    def test_employee_cannot_retrieve_user(self, employee_client):
        user = UserFactory()
        res = employee_client.get(f"/api/users/{user.id}/")
        assert res.status_code == 403

    # partial_update
    def test_admin_can_update_user(self, admin_client):
        user = UserFactory()
        res = admin_client.patch(f"/api/users/{user.id}/")
        assert res.status_code == 200

    def test_manager_can_update_user(self, manager_client, manager_user):
        # manager може оновити дані користувача зі своєї team
        user = UserFactory(team=manager_user.team)
        res = manager_client.patch(f"/api/users/{user.id}/")
        assert res.status_code == 200

        # manager не може оновити дані користувача не зі своєї team
        user = UserFactory()
        res = manager_client.patch(f"/api/users/{user.id}/")
        assert res.status_code == 404

    def test_sales_rep_cannot_update_user(self, sales_rep_client):
        user = UserFactory()
        res = sales_rep_client.patch(f"/api/users/{user.id}/")
        assert res.status_code == 403

    def test_employee_cannot_update_user(self, employee_client):
        user = UserFactory()
        res = employee_client.patch(f"/api/users/{user.id}/")
        assert res.status_code == 403

    # delete
    def test_admin_can_delete_user(self, admin_client):
        user = UserFactory()
        res = admin_client.delete(f"/api/users/{user.id}/")
        assert res.status_code == 204

    def test_manager_cannot_delete_user(self, manager_client):
        user = UserFactory()
        res = manager_client.delete(f"/api/users/{user.id}/")
        assert res.status_code == 403

    def test_sales_rep_cannot_delete_user(self, sales_rep_client):
        user = UserFactory()
        res = sales_rep_client.delete(f"/api/users/{user.id}/")
        assert res.status_code == 403

    def test_employee_cannot_delete_user(self, employee_client):
        user = UserFactory()
        res = employee_client.delete(f"/api/users/{user.id}/")
        assert res.status_code == 403

    # /api/users/me/
    def test_admin_can_list_users_me(self, admin_client):
        res = admin_client.get("/api/users/me/")
        assert res.status_code == 200

    def test_manager_can_list_users_me(self, manager_client):
        res = manager_client.get("/api/users/me/")
        assert res.status_code == 200

    def test_sales_rep_can_list_users_me(self, sales_rep_client):
        res = sales_rep_client.get("/api/users/me/")
        assert res.status_code == 200

    def test_employee_can_list_users_me(self, employee_client):
        res = employee_client.get("/api/users/me/")
        assert res.status_code == 200

    def test_admin_can_update_users_me(self, admin_client):
        res = admin_client.patch("/api/users/me/")
        assert res.status_code == 200

    def test_manager_can_update_users_me(self, manager_client):
        res = manager_client.patch("/api/users/me/")
        assert res.status_code == 200

    def test_sales_rep_can_update_users_me(self, sales_rep_client):
        res = sales_rep_client.patch("/api/users/me/")
        assert res.status_code == 200

    def test_employee_can_update_users_me(self, employee_client):
        res = employee_client.patch("/api/users/me/")
        assert res.status_code == 200


@pytest.mark.django_db
class TestUsersEndpoint:
    # тестує, які дані повертаються

    # /api/users/
    # GET
    def test_admin_can_see_all_users(self, admin_client, admin_user):
        users = UserFactory.create_batch(3)  # створює 3 users
        res = admin_client.get("/api/users/")
        assert len(res.data) == 4  # 3 users + admin

        # список з id, які повинні повернутись
        users_id = [str(admin_user.id)] + [str(user.id) for user in users]

        # перевіряємо, чи повернулися дані саме створених користувачів і адміна
        for user_data in res.data:
            assert user_data["id"] in users_id

    def test_manager_can_see_only_team_users(self, manager_client, manager_user):
        # users з тієї самої команди
        users = UserFactory.create_batch(2, team=manager_user.team)
        # users з іншої команди
        UserFactory.create_batch(4)

        res = manager_client.get("/api/users/")
        assert len(res.data) == 3  # бачить тільки свою команду: себе і ще двох users

        # список з id, які повинні повернутись
        users_id = [str(manager_user.id)] + [str(user.id) for user in users]

        # перевіряємо, чи повернулися дані саме створених користувачів і manager
        for user_data in res.data:
            assert user_data["id"] in users_id

    def test_response_fields(self, admin_client, admin_user):
        res = admin_client.get("/api/users/")
        user_data = res.data[0]
        # перевіряємо, що повертаються правильні поля
        assert user_data["id"] == str(admin_user.id)
        assert user_data["email"] == admin_user.email
        assert user_data["first_name"] == admin_user.first_name
        assert user_data["last_name"] == admin_user.last_name
        assert str(admin_user.avatar) in user_data["avatar"]  # тут перевіряється шлях до файлу
        assert user_data["role"] == admin_user.role
        assert user_data["is_active"] == admin_user.is_active
        assert user_data["is_verified"] == admin_user.is_verified
        assert parse_datetime(user_data["created_at"]) == admin_user.created_at
        assert user_data["team"] == admin_user.team.id
        # пароль не повинен повертатись
        assert "password" not in user_data

    # /api/users/{user-id}/
    # retrieve
    def test_admin_can_retrieve_users(self, admin_client, admin_user):
        # admin отримує свої дані
        res = admin_client.get(f"/api/users/{admin_user.id}/")
        assert res.data["id"] == str(admin_user.id)

        # admin отримує дані користувача
        user = UserFactory()
        res = admin_client.get(f"/api/users/{user.id}/")
        assert res.data["id"] == str(user.id)

    def test_manager_can_retrieve_users(self, manager_client, manager_user):
        # manager отримує дані користувача
        user = UserFactory(team=manager_user.team)
        res = manager_client.get(f"/api/users/{user.id}/")
        assert res.data["id"] == str(user.id)

    # partial_update
    def test_admin_can_update_user(self, admin_client):
        user = UserFactory()
        default_avatar = user.avatar.name
        new_avatar = create_test_image()
        new_data = {
            "first_name": "new_name",
            "last_name": "new_last_name",
            "avatar": new_avatar,
            "role": "manager",
            "is_active": False,
        }
        res = admin_client.patch(f"/api/users/{user.id}/", data=new_data, format="multipart")

        assert res.status_code == 200
        user.refresh_from_db()
        assert user.first_name == "new_name"
        assert user.last_name == "new_last_name"
        assert user.avatar.name != default_avatar
        assert user.role == "manager"
        assert user.is_active is False

    def test_manager_can_update_user(self, manager_client, manager_user):
        user = UserFactory(team=manager_user.team)
        default_avatar = user.avatar.name
        new_avatar = create_test_image()
        new_data = {
            "first_name": "new_name",
            "last_name": "new_last_name",
            "avatar": new_avatar,
            "is_active": False,
        }
        res = manager_client.patch(f"/api/users/{user.id}/", data=new_data, format="multipart")

        assert res.status_code == 200
        user.refresh_from_db()
        assert user.first_name == "new_name"
        assert user.last_name == "new_last_name"
        assert user.avatar.name != default_avatar
        assert user.is_active is False

    def test_readonly_fields_are_ignored_on_update(self, admin_client):
        user = UserFactory()
        new_data = {
            "id": "00000000-0000-0000-0000-000000000000",
            "email": "new_email@test.com",
            "created_at": "2026-01-01T10:00:00Z",
            "is_verified": False,
            "team": "00000000-0000-0000-0000-000000000000",
        }
        res = admin_client.patch(f"/api/users/{user.id}/", data=new_data, format="json")

        assert res.status_code == 200
        user.refresh_from_db()
        assert user.id != new_data["id"]
        assert user.email != new_data["email"]
        assert user.created_at != new_data["created_at"]
        assert user.is_verified != new_data["is_verified"]
        assert user.team != new_data["team"]

    def test_manager_cannot_change_role(self, manager_client):
        user = UserFactory()
        res = manager_client.patch(f"/api/users/{user.id}/", data={"role": "manager"}, format="json")
        assert res.status_code == 404

    # delete
    def test_admin_can_delete_user(self, admin_client):
        user = UserFactory()
        admin_client.delete(f"/api/users/{user.id}/")
        assert not User.objects.filter(id=user.id).exists()

    def test_all_user_data_is_archived_when_user_is_deleted(self, admin_client):
        user = UserFactory()
        pipeline = PipelineFactory(assigned_to=user)
        deal = DealFactory(pipeline=pipeline, assigned_to=user)
        activity = ActivityFactory(deal=deal, assigned_to=user)

        admin_client.delete(f"/api/users/{user.id}/")

        pipeline.refresh_from_db()
        assert pipeline.archived is not None
        deal.refresh_from_db()
        assert deal.archived is not None
        activity.refresh_from_db()
        assert activity.archived is not None

        # додаткова перевірка, що всі дані є в одній архівації
        assert pipeline.archived == deal.archived == activity.archived

        # перевірка типу архівації
        assert pipeline.archived.archiving_type == ArchivingType.USER_DELETED

    # /api/users/me/
    # GET
    def test_admin_can_list_users_me(self, admin_client, admin_user):
        res = admin_client.get("/api/users/me/")
        user_data = res.data
        # перевіряємо, що повертаються правильні поля
        assert user_data["id"] == str(admin_user.id)
        assert user_data["email"] == admin_user.email
        assert user_data["first_name"] == admin_user.first_name
        assert user_data["last_name"] == admin_user.last_name
        assert admin_user.avatar.name in user_data["avatar"]
        assert user_data["role"] == admin_user.role
        assert user_data["team"] == admin_user.team.id
        assert parse_datetime(user_data["created_at"]) == admin_user.created_at
        # поля, які не повинні повертатись
        assert "password" not in user_data
        assert "is_active" not in user_data
        assert "is_verified" not in user_data

    def test_manager_can_list_users_me(self, manager_client, manager_user):
        res = manager_client.get("/api/users/me/")
        user_data = res.data
        # перевіряємо, що повертаються правильні поля
        assert user_data["id"] == str(manager_user.id)
        assert user_data["email"] == manager_user.email
        assert user_data["first_name"] == manager_user.first_name
        assert user_data["last_name"] == manager_user.last_name
        assert manager_user.avatar.name in user_data["avatar"]
        assert user_data["role"] == manager_user.role
        assert user_data["team"] == manager_user.team.id
        assert parse_datetime(user_data["created_at"]) == manager_user.created_at
        # поля, які не повинні повертатись
        assert "password" not in user_data
        assert "is_active" not in user_data
        assert "is_verified" not in user_data

    def test_sales_rep_can_list_users_me(self, sales_rep_client, sales_rep_user):
        res = sales_rep_client.get("/api/users/me/")
        user_data = res.data
        # перевіряємо, що повертаються правильні поля
        assert user_data["id"] == str(sales_rep_user.id)
        assert user_data["email"] == sales_rep_user.email
        assert user_data["first_name"] == sales_rep_user.first_name
        assert user_data["last_name"] == sales_rep_user.last_name
        assert sales_rep_user.avatar.name in user_data["avatar"]
        assert user_data["role"] == sales_rep_user.role
        assert user_data["team"] == sales_rep_user.team.id
        assert parse_datetime(user_data["created_at"]) == sales_rep_user.created_at
        # поля, які не повинні повертатись
        assert "password" not in user_data
        assert "is_active" not in user_data
        assert "is_verified" not in user_data

    def test_employee_rep_can_list_users_me(self, employee_client, employee_user):
        res = employee_client.get("/api/users/me/")
        user_data = res.data
        # перевіряємо, що повертаються правильні поля
        assert user_data["id"] == str(employee_user.id)
        assert user_data["email"] == employee_user.email
        assert user_data["first_name"] == employee_user.first_name
        assert user_data["last_name"] == employee_user.last_name
        assert employee_user.avatar.name in user_data["avatar"]
        assert user_data["role"] == employee_user.role
        assert user_data["team"] == employee_user.team.id
        assert parse_datetime(user_data["created_at"]) == employee_user.created_at
        # поля, які не повинні повертатись
        assert "password" not in user_data
        assert "is_active" not in user_data
        assert "is_verified" not in user_data

    # PATCH
    def test_admin_can_update_users_me(self, admin_client, admin_user):
        admin_avatar = admin_user.avatar.name
        new_avatar = create_test_image()
        new_data = {
            "first_name": "new_name",
            "last_name": "new_last_name",
            "avatar": new_avatar,
        }
        res = admin_client.patch(f"/api/users/me/", data=new_data, format="multipart")
        assert res.status_code == 200

        admin_user.refresh_from_db()
        assert admin_user.first_name == "new_name"
        assert admin_user.last_name == "new_last_name"
        assert admin_user.avatar.name != admin_avatar

    def test_manager_can_update_users_me(self, manager_client, manager_user):
        manager_avatar = manager_user.avatar.name
        new_avatar = create_test_image()
        new_data = {
            "first_name": "new_name",
            "last_name": "new_last_name",
            "avatar": new_avatar,
        }
        res = manager_client.patch(f"/api/users/me/", data=new_data, format="multipart")
        assert res.status_code == 200

        manager_user.refresh_from_db()
        assert manager_user.first_name == "new_name"
        assert manager_user.last_name == "new_last_name"
        assert manager_user.avatar.name != manager_avatar

    def test_sales_rep_can_update_users_me(self, sales_rep_client, sales_rep_user):
        sales_rep_avatar = sales_rep_user.avatar.name
        new_avatar = create_test_image()
        new_data = {
            "first_name": "new_name",
            "last_name": "new_last_name",
            "avatar": new_avatar,
        }
        res = sales_rep_client.patch(f"/api/users/me/", data=new_data, format="multipart")
        assert res.status_code == 200

        sales_rep_user.refresh_from_db()
        assert sales_rep_user.first_name == "new_name"
        assert sales_rep_user.last_name == "new_last_name"
        assert sales_rep_user.avatar.name != sales_rep_avatar

    def test_employee_can_update_users_me(self, employee_client, employee_user):
        employee_avatar = employee_user.avatar.name
        new_avatar = create_test_image()
        new_data = {
            "first_name": "new_name",
            "last_name": "new_last_name",
            "avatar": new_avatar,
        }
        res = employee_client.patch(f"/api/users/me/", data=new_data, format="multipart")
        assert res.status_code == 200

        employee_user.refresh_from_db()
        assert employee_user.first_name == "new_name"
        assert employee_user.last_name == "new_last_name"
        assert employee_user.avatar.name != employee_avatar

    def test_user_cannot_change_protected_fields(self, admin_client, admin_user):
        new_data = {
            "id": "00000000-0000-0000-0000-000000000000",
            "email": "new_email@test.com",
            "role": "manager",
            "created_at": "2026-01-01T10:00:00Z",
            "is_verified": False,
            "team": "00000000-0000-0000-0000-000000000000",
        }
        res = admin_client.patch(f"/api/users/me/", data=new_data, format="json")

        assert res.status_code == 200
        admin_user.refresh_from_db()
        assert str(admin_user.id) != new_data["id"]
        assert admin_user.email != new_data["email"]
        assert admin_user.role != new_data["role"]
        assert parse_datetime(new_data["created_at"]) != admin_user.created_at
        assert admin_user.is_verified != new_data["is_verified"]
        assert str(admin_user.team.id) != new_data["team"]
