import pytest

from auth_app.tests.factories import TeamFactory, UserFactory
from crm_app.tests.factories import (
    ProductFactory,
    PipelineFactory,
    DealFactory,
    ActivityFactory,
)
from auth_app.models import Team
from crm_app.models import ArchivingType


@pytest.mark.django_db
class TestTeamsEndpoint:
    # /api/teams/
    # GET
    def test_admin_can_list_teams(self, admin_client, admin_user):
        teams = TeamFactory.create_batch(3)
        res = admin_client.get("/api/teams/")
        assert res.status_code == 200
        assert len(res.data) == 4  # 3 створених teams + admin.team

        teams_id = [str(admin_user.team.id)] + [str(team.id) for team in teams]  # список з id, які повинні повернутись

        # перевіряємо, чи повернулися дані саме створених teams і team адміна
        for team_data in res.data:
            assert team_data["id"] in teams_id

    def test_manager_can_list_only_own_teams(self, manager_client, manager_user):
        manager_team = manager_user.team
        TeamFactory.create_batch(3)

        res = manager_client.get("/api/teams/")
        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["id"] == str(manager_team.id)

    def test_sales_rep_cannot_list_teams(self, sales_rep_client):
        res = sales_rep_client.get("/api/teams/")
        assert res.status_code == 403

    def test_employee_cannot_list_teams(self, employee_client):
        res = employee_client.get("/api/teams/")
        assert res.status_code == 403

    def test_unauthenticated_cannot_list_teams(self, api_client):
        res = api_client.get("/api/teams/")
        assert res.status_code == 401

    def test_response_fields(self, admin_client, admin_user):
        team = admin_user.team
        team.products.add(ProductFactory())
        res = admin_client.get("/api/teams/")
        team_data = res.data[0]
        # перевіряємо, що повертаються правильні поля
        assert team_data["id"] == str(team.id)
        assert team_data["name"] == team.name
        assert list(str(user_id) for user_id in team_data["users"]) == list(str(user.id) for user in team.users.all())
        assert (list(str(product_id) for product_id in team_data["products"]) ==
                list(str(product.id) for product in team.products.all()))

    # POST
    def test_admin_can_create_teams(self, admin_client):
        res = admin_client.post("/api/teams/", data={"name": "Test"}, format="json")
        assert res.status_code == 201

        team = Team.objects.get(id=res.data["id"])
        assert team.name == "Test"

    def test_manager_cannot_create_teams(self, manager_client):
        res = manager_client.post("/api/teams/", data={"name": "Test"}, format="json")
        assert res.status_code == 403

    def test_sales_rep_cannot_create_teams(self, sales_rep_client):
        res = sales_rep_client.post("/api/teams/", data={"name": "Test"}, format="json")
        assert res.status_code == 403

    def test_employee_cannot_create_teams(self, employee_client):
        res = employee_client.post("/api/teams/", data={"name": "Test"}, format="json")
        assert res.status_code == 403

    def test_create_team_without_required_fields(self, admin_client):
        res = admin_client.post("/api/teams/")
        assert res.status_code == 400

    def test_readonly_fields_are_ignored_on_create(self, admin_client):
        users = UserFactory.create_batch(3)
        products = ProductFactory.create_batch(3)
        new_data = {
            "id": "00000000-0000-0000-0000-000000000000",
            "name": "Test",
            "users": [str(user) for user in users],
            "products": [str(product) for product in products],
        }
        res = admin_client.post(f"/api/teams/", data=new_data, format="json")
        assert res.status_code == 201

        team = Team.objects.get(id=res.data["id"])
        assert str(team.id) != new_data["id"]
        assert team.name == new_data["name"]
        assert list(str(user.id) for user in team.users.all()) == []
        assert list(str(product.id) for product in team.products.all()) == []

    # /api/teams/{team-id}/
    # retrieve
    def test_admin_can_retrieve_team(self, admin_client):
        team = TeamFactory()
        res = admin_client.get(f"/api/teams/{team.id}/")
        assert res.status_code == 200

        # перевіряємо, що повертаються правильні поля
        team_data = res.data
        assert team_data["id"] == str(team.id)
        assert team_data["name"] == team.name
        assert list(str(user_id) for user_id in team_data["users"]) == list(str(user.id) for user in team.users.all())
        assert (list(str(product_id) for product_id in team_data["products"]) ==
                list(str(product.id) for product in team.products.all()))

    def test_manager_can_retrieve_only_own_team(self, manager_client, manager_user):
        # manager може отримати доступ до своєї team
        team = manager_user.team
        res = manager_client.get(f"/api/teams/{team.id}/")
        assert res.status_code == 200

        # перевіряємо, що повертаються правильні поля
        team_data = res.data
        assert team_data["id"] == str(team.id)
        assert team_data["name"] == team.name
        assert list(str(user_id) for user_id in team_data["users"]) == list(str(user.id) for user in team.users.all())
        assert (list(str(product_id) for product_id in team_data["products"]) ==
                list(str(product.id) for product in team.products.all()))

        # manager не може отримати доступ до не своєї team
        team = TeamFactory()
        res = manager_client.get(f"/api/teams/{team.id}/")
        assert res.status_code == 404

    def test_sales_rep_cannot_retrieve_team(self, sales_rep_client):
        team = TeamFactory()
        res = sales_rep_client.get(f"/api/teams/{team.id}/")
        assert res.status_code == 403

    def test_employee_cannot_retrieve_team(self, employee_client):
        team = TeamFactory()
        res = employee_client.get(f"/api/teams/{team.id}/")
        assert res.status_code == 403

    # partial_update
    def test_admin_can_update_team(self, admin_client):
        team = TeamFactory()
        res = admin_client.patch(f"/api/teams/{team.id}/", data={"name": "New Name"}, format="json")
        assert res.status_code == 200

        team.refresh_from_db()
        assert team.name == "New Name"

    def test_manager_can_update_only_own_team(self, manager_client, manager_user):
        # manager може оновити дані своєї team
        team = manager_user.team
        res = manager_client.patch(f"/api/teams/{team.id}/", data={"name": "New Name"}, format="json")
        assert res.status_code == 200

        team.refresh_from_db()
        assert team.name == "New Name"

        # manager не може оновити дані не своєї team
        team = TeamFactory(name="Test Team")
        res = manager_client.patch(f"/api/teams/{team.id}/", data={"name": "New Name"}, format="json")
        assert res.status_code == 404

        team.refresh_from_db()
        assert team.name == "Test Team"

    def test_sales_rep_cannot_update_team(self, sales_rep_client):
        team = TeamFactory()
        res = sales_rep_client.patch(f"/api/teams/{team.id}/")
        assert res.status_code == 403

    def test_employee_cannot_update_team(self, employee_client):
        team = TeamFactory()
        res = employee_client.patch(f"/api/teams/{team.id}/")
        assert res.status_code == 403

    def test_readonly_fields_are_ignored_on_update(self, admin_client):
        team = TeamFactory()
        users = UserFactory.create_batch(3)
        products = ProductFactory.create_batch(3)
        new_data = {
            "id": "00000000-0000-0000-0000-000000000000",
            "users": [str(user.id) for user in users],
            "products": [str(product.id) for product in products],
        }
        res = admin_client.patch(f"/api/teams/{team.id}/", data=new_data, format="json")
        assert res.status_code == 200

        team.refresh_from_db()
        assert team.id != new_data["id"]
        assert team.users != new_data["users"]
        assert team.products != new_data["products"]

    # delete
    def test_admin_can_delete_team(self, admin_client):
        team = TeamFactory()
        res = admin_client.delete(f"/api/teams/{team.id}/")
        assert res.status_code == 204
        assert not Team.objects.filter(id=team.id).exists()

    def test_all_team_users_data_is_archived_when_team_is_deleted(self, admin_client):

        team = TeamFactory()
        user = UserFactory(team=team)
        pipeline = PipelineFactory(assigned_to=user)
        deal = DealFactory(pipeline=pipeline, assigned_to=user)
        activity = ActivityFactory(deal=deal, assigned_to=user)

        res = admin_client.delete(f"/api/teams/{team.id}/")

        pipeline.refresh_from_db()
        assert pipeline.archived is not None
        deal.refresh_from_db()
        assert deal.archived is not None
        activity.refresh_from_db()
        assert activity.archived is not None

        # додаткова перевірка, що всі дані є в одній архівації
        assert pipeline.archived == deal.archived == activity.archived

        # перевірка типу архівації
        assert pipeline.archived.archiving_type == ArchivingType.TEAM_DELETED

    def test_manager_cannot_delete_team(self, manager_client):
        team = TeamFactory()
        res = manager_client.delete(f"/api/teams/{team.id}/")
        assert res.status_code == 403

    def test_sales_rep_cannot_delete_team(self, sales_rep_client):
        team = TeamFactory()
        res = sales_rep_client.delete(f"/api/teams/{team.id}/")
        assert res.status_code == 403

    def test_employee_cannot_delete_team(self, employee_client):
        team = TeamFactory()
        res = employee_client.delete(f"/api/teams/{team.id}/")
        assert res.status_code == 403


@pytest.mark.django_db
class TestTeamsAddUserEndpoint:
    # /api/teams/{team-id}/add-user/
    def test_admin_can_add_user(self, admin_client):
        team = TeamFactory()
        user = UserFactory(team=None)
        res = admin_client.post(f"/api/teams/{team.id}/add-user/", data={"user": str(user.id)}, format="json")
        assert res.status_code == 200
        # перевірка, чи дійсно user було додано до team
        user.refresh_from_db()
        assert user.team == team

    def test_pipeline_is_created_when_user_is_added_to_team(self, admin_client):
        # чи створюються pipeline для user під product, з якими вже працює team, до якої було додано user
        team = TeamFactory()
        user = UserFactory(team=None)
        product1 = ProductFactory()
        product2 = ProductFactory()
        team.products.add(product1, product2)

        res = admin_client.post(f"/api/teams/{team.id}/add-user/", data={"user": str(user.id)}, format="json")

        user.refresh_from_db()
        assert user.pipelines.count() == 2
        assert user.pipelines.filter(product=product1).exists()
        assert user.pipelines.filter(product=product2).exists()

    def test_add_user_already_in_same_team_fails(self, admin_client):
        team = TeamFactory()
        user = UserFactory(team=team)
        res = admin_client.post(f"/api/teams/{team.id}/add-user/", data={"user": str(user.id)}, format="json")
        assert res.status_code == 400

    def test_add_user_already_in_other_team_fails(self, admin_client):
        team = TeamFactory()
        user = UserFactory()
        res = admin_client.post(f"/api/teams/{team.id}/add-user/", data={"user": str(user.id)}, format="json")
        assert res.status_code == 400
        team.refresh_from_db()
        assert user not in team.users.all()

    def test_manager_cannot_add_user(self, manager_client):
        team = TeamFactory()
        user = UserFactory(team=None)
        res = manager_client.post(f"/api/teams/{team.id}/add-user/", data={"user": str(user.id)}, format="json")
        assert res.status_code == 403

    def test_sales_rep_cannot_add_user(self, sales_rep_client):
        team = TeamFactory()
        user = UserFactory(team=None)
        res = sales_rep_client.post(f"/api/teams/{team.id}/add-user/", data={"user": str(user.id)}, format="json")
        assert res.status_code == 403

    def test_employee_cannot_add_user(self, employee_client):
        team = TeamFactory()
        user = UserFactory(team=None)
        res = employee_client.post(f"/api/teams/{team.id}/add-user/", data={"user": str(user.id)}, format="json")
        assert res.status_code == 403


@pytest.mark.django_db
class TestTeamsRemoveUserEndpoint:
    # /api/teams/{team-id}/remove-user/
    def test_admin_can_remove_user(self, admin_client):
        team = TeamFactory()
        user = UserFactory(team=team)
        res = admin_client.post(f"/api/teams/{team.id}/remove-user/", data={"user": str(user.id)}, format="json")
        assert res.status_code == 200
        team.refresh_from_db()
        assert user not in team.users.all()

    def test_user_data_is_archived_when_user_is_removed_from_team(self, admin_client):
        team = TeamFactory()
        user = UserFactory(team=team)
        pipeline = PipelineFactory(assigned_to=user)
        deal = DealFactory(pipeline=pipeline, assigned_to=user)
        activity = ActivityFactory(deal=deal, assigned_to=user)

        res = admin_client.post(f"/api/teams/{team.id}/remove-user/", data={"user": str(user.id)}, format="json")

        pipeline.refresh_from_db()
        assert pipeline.archived is not None
        deal.refresh_from_db()
        assert deal.archived is not None
        activity.refresh_from_db()
        assert activity.archived is not None

        # додаткова перевірка, що всі дані є в одній архівації
        assert pipeline.archived == deal.archived == activity.archived

        # перевірка типу архівації
        assert pipeline.archived.archiving_type == ArchivingType.USER_REMOVED_FROM_TEAM

    def test_manager_can_remove_user(self, manager_client, manager_user):
        team = manager_user.team
        user = UserFactory(team=team)
        res = manager_client.post(f"/api/teams/{team.id}/remove-user/", data={"user": str(user.id)}, format="json")
        assert res.status_code == 200
        team.refresh_from_db()
        assert user not in team.users.all()

    def test_remove_user_not_in_team_fails(self, admin_client):
        team = TeamFactory()
        user = UserFactory()
        res = admin_client.post(f"/api/teams/{team.id}/remove-user/", data={"user": str(user.id)}, format="json")
        assert res.status_code == 400

    def test_sales_rep_cannot_remove_user(self, sales_rep_client):
        team = TeamFactory()
        user = UserFactory(team=team)
        res = sales_rep_client.post(f"/api/teams/{team.id}/remove-user/", data={"user": str(user.id)}, format="json")
        assert res.status_code == 403

    def test_employee_cannot_remove_user(self, employee_client):
        team = TeamFactory()
        user = UserFactory(team=team)
        res = employee_client.post(f"/api/teams/{team.id}/remove-user/", data={"user": str(user.id)}, format="json")
        assert res.status_code == 403


@pytest.mark.django_db
class TestTeamsAddProductEndpoint:
    # /api/teams/{team-id}/add-product/
    def test_admin_can_add_product(self, admin_client):
        team = TeamFactory()
        product = ProductFactory()
        res = admin_client.post(f"/api/teams/{team.id}/add-product/", data={"product": str(product.id)}, format="json")
        assert res.status_code == 200
        team.refresh_from_db()
        assert product in team.products.all()

    def test_pipeline_is_created_for_all_team_users_when_product_is_added(self, admin_client, admin_user):
        # чи створюються pipeline для усіх users з team під доданий product
        team = admin_user.team
        user1 = UserFactory(team=team)
        user2 = UserFactory(team=team)
        product = ProductFactory()

        res = admin_client.post(f"/api/teams/{team.id}/add-product/", data={"product": str(product.id)}, format="json")

        admin_user.refresh_from_db()
        assert admin_user.pipelines.count() == 1
        assert admin_user.pipelines.filter(product=product).exists()
        user1.refresh_from_db()
        assert user1.pipelines.count() == 1
        assert user1.pipelines.filter(product=product).exists()
        user2.refresh_from_db()
        assert user2.pipelines.count() == 1
        assert user2.pipelines.filter(product=product).exists()

    def test_manager_can_add_product(self, manager_client, manager_user):
        team = manager_user.team
        product = ProductFactory()
        res = manager_client.post(f"/api/teams/{team.id}/add-product/", data={"product": str(product.id)}, format="json")
        assert res.status_code == 200
        team.refresh_from_db()
        assert product in team.products.all()

    def test_add_product_already_added_fails(self, admin_client):
        team = TeamFactory()
        product = ProductFactory()
        team.products.add(product)
        res = admin_client.post(f"/api/teams/{team.id}/add-product/", data={"product": str(product.id)}, format="json")
        assert res.status_code == 400

    def test_sales_rep_cannot_add_product(self, sales_rep_client):
        team = TeamFactory()
        product = ProductFactory()
        res = sales_rep_client.post(
            f"/api/teams/{team.id}/add-product/",
            data={"product": str(product.id)},
            format="json",
        )
        assert res.status_code == 403

    def test_employee_cannot_add_product(self, employee_client):
        team = TeamFactory()
        product = ProductFactory()
        res = employee_client.post(
            f"/api/teams/{team.id}/add-product/",
            data={"product": str(product.id)},
            format="json"
        )
        assert res.status_code == 403


@pytest.mark.django_db
class TestTeamsRemoveProductEndpoint:
    # /api/teams/{team-id}/remove-product/
    def test_admin_can_remove_product(self, admin_client):
        team = TeamFactory()
        product = ProductFactory()
        team.products.add(product)
        assert product in team.products.all()
        res = admin_client.post(
            f"/api/teams/{team.id}/remove-product/",
            data={"product": str(product.id)},
            format="json"
        )
        assert res.status_code == 200
        team.refresh_from_db()
        assert product not in team.products.all()

    def test_all_team_users_data_is_archived_when_product_is_removed(self, admin_client):
        # перевіряє, чи архівуються всі дані користувачів команди, які стосувались видаленого продукту
        team = TeamFactory()
        product = ProductFactory()
        team.products.add(product)

        user = UserFactory(team=team)
        pipeline = PipelineFactory(assigned_to=user, product=product)
        deal = DealFactory(pipeline=pipeline, assigned_to=user)
        activity = ActivityFactory(deal=deal, assigned_to=user)

        res = admin_client.post(
            f"/api/teams/{team.id}/remove-product/",
            data={"product": str(product.id)},
            format="json"
        )

        pipeline.refresh_from_db()
        assert pipeline.archived is not None
        deal.refresh_from_db()
        assert deal.archived is not None
        activity.refresh_from_db()
        assert activity.archived is not None

        # додаткова перевірка, що всі дані є в одній архівації
        assert pipeline.archived == deal.archived == activity.archived

        # перевірка типу архівації
        assert pipeline.archived.archiving_type == ArchivingType.PRODUCT_REMOVED_FROM_TEAM

    def test_manager_can_remove_product(self, manager_client, manager_user):
        team = manager_user.team
        product = ProductFactory()
        team.products.add(product)
        res = manager_client.post(
            f"/api/teams/{team.id}/remove-product/",
            data={"product": str(product.id)},
            format="json"
        )
        assert res.status_code == 200
        team.refresh_from_db()
        assert product not in team.products.all()

    def test_remove_product_not_added_fails(self, admin_client):
        team = TeamFactory()
        product = ProductFactory()
        res = admin_client.post(
            f"/api/teams/{team.id}/remove-product/",
            data={"product": str(product.id)},
            format="json"
        )
        assert res.status_code == 400

    def test_sales_rep_cannot_remove_product(self, sales_rep_client):
        team = TeamFactory()
        product = ProductFactory()
        team.products.add(product)
        res = sales_rep_client.post(
            f"/api/teams/{team.id}/remove-product/",
            data={"product": str(product.id)},
            format="json"
        )
        assert res.status_code == 403

    def test_employee_cannot_remove_product(self, employee_client):
        team = TeamFactory()
        product = ProductFactory()
        team.products.add(product)
        res = employee_client.post(
            f"/api/teams/{team.id}/remove-product/",
            data={"product": str(product.id)},
            format="json"
        )
        assert res.status_code == 403
