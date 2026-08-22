import pytest

from .factories import ProductFactory, PipelineFactory, DealFactory, ActivityFactory
from crm_app.models import Product, ArchivingType
from auth_app.tests.factories import TeamFactory


@pytest.mark.django_db
class TestProductsEndpoint:
    # /api/products/
    # GET
    def test_admin_can_list_products(self, admin_client):
        ProductFactory.create_batch(3)
        res = admin_client.get("/api/products/")
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_manager_can_list_products(self, manager_client):
        ProductFactory.create_batch(3)
        res = manager_client.get("/api/products/")
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_sales_rep_can_list_products(self, sales_rep_client):
        ProductFactory.create_batch(3)
        res = sales_rep_client.get("/api/products/")
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_sales_rep_list_products_hides_teams(self, sales_rep_client):
        ProductFactory()
        res = sales_rep_client.get(f"/api/products/")
        assert "teams" not in res.data[0]

    def test_employee_cannot_list_products(self, employee_client):
        ProductFactory.create_batch(3)
        res = employee_client.get("/api/products/")
        assert res.status_code == 403

    def test_unauthenticated_cannot_list_products(self, api_client):
        ProductFactory.create_batch(3)
        res = api_client.get("/api/products/")
        assert res.status_code == 401

    def test_list_response_fields(self, admin_client):
        product = ProductFactory()
        res = admin_client.get("/api/products/")

        product_data = res.data[0]
        assert product_data["id"] == str(product.id)
        assert product_data["name"] == product.name
        assert product_data["description"] == product.description
        assert (list(str(team_id) for team_id in product_data["teams"]) ==
                list(str(team.id) for team in product.teams.all()))

    # POST
    def test_admin_can_create_product(self, admin_client):
        res = admin_client.post("/api/products/", data={"name": "test"}, format="json")
        assert res.status_code == 201

        product = Product.objects.get(id=res.data["id"])
        assert product.name == "test"

    def test_manager_can_create_product(self, manager_client):
        res = manager_client.post("/api/products/", data={"name": "test"}, format="json")
        assert res.status_code == 201

        product = Product.objects.get(id=res.data["id"])
        assert product.name == "test"

    def test_sales_rep_cannot_create_product(self, sales_rep_client):
        res = sales_rep_client.post("/api/products/", data={"name": "test"}, format="json")
        assert res.status_code == 403

    def test_employee_cannot_create_product(self, employee_client):
        res = employee_client.post("/api/products/", data={"name": "test"}, format="json")
        assert res.status_code == 403

    def test_create_product_without_required_field_fails(self, admin_client):
        res = admin_client.post("/api/products/")
        assert res.status_code == 400
        assert "name" in res.data

    # /api/products/{product-id}/
    # retrieve
    def test_admin_can_retrieve_product(self, admin_client):
        product = ProductFactory()
        res = admin_client.get(f"/api/products/{product.id}/")
        assert res.status_code == 200

    def test_manager_can_retrieve_product(self, manager_client):
        product = ProductFactory()
        res = manager_client.get(f"/api/products/{product.id}/")
        assert res.status_code == 200

    def test_sales_rep_can_retrieve_product(self, sales_rep_client):
        product = ProductFactory()
        res = sales_rep_client.get(f"/api/products/{product.id}/")
        assert res.status_code == 200

    def test_sales_rep_retrieve_product_hides_teams(self, sales_rep_client):
        product = ProductFactory()
        res = sales_rep_client.get(f"/api/products/{product.id}/")
        assert "teams" not in res.data

    def test_employee_cannot_retrieve_product(self, employee_client):
        product = ProductFactory()
        res = employee_client.get(f"/api/products/{product.id}/")
        assert res.status_code == 403

    def test_retrieve_response_fields(self, admin_client):
        product = ProductFactory()
        res = admin_client.get(f"/api/products/{product.id}/")

        # перевіряємо, що повертаються правильні поля
        product_data = res.data
        assert product_data["id"] == str(product.id)
        assert product_data["name"] == product.name
        assert product_data["description"] == product.description
        assert (list(str(team_id) for team_id in product_data["teams"]) ==
                list(str(team.id) for team in product.teams.all()))

    # partial_update
    def test_admin_can_update_product(self, admin_client):
        product = ProductFactory()
        new_product_data = {
            "name": "New name",
            "description": "New description",
        }
        res = admin_client.patch(f"/api/products/{product.id}/", data=new_product_data, format="json")
        assert res.status_code == 200

        product.refresh_from_db()
        assert product.name == new_product_data["name"]
        assert product.description == new_product_data["description"]

    def test_manager_can_update_product(self, manager_client):
        product = ProductFactory()
        new_product_data = {
            "name": "New name",
            "description": "New description",
        }
        res = manager_client.patch(f"/api/products/{product.id}/", data=new_product_data, format="json")
        assert res.status_code == 200

        product.refresh_from_db()
        assert product.name == new_product_data["name"]
        assert product.description == new_product_data["description"]

    def test_sales_rep_cannot_update_product(self, sales_rep_client):
        product = ProductFactory()
        res = sales_rep_client.patch(f"/api/products/{product.id}/", data={}, format="json")
        assert res.status_code == 403

    def test_employee_cannot_update_product(self, employee_client):
        product = ProductFactory()
        res = employee_client.patch(f"/api/products/{product.id}/", data={}, format="json")
        assert res.status_code == 403

    def test_readonly_fields_are_ignored_on_update(self, admin_client):
        product = ProductFactory()
        teams = TeamFactory.create_batch(3)
        new_data = {
            "id": "00000000-0000-0000-0000-000000000000",
            "deals": [str(team.id) for team in teams],
        }
        res = admin_client.patch(f"/api/products/{product.id}/", data=new_data, format="json")
        assert res.status_code == 200

        product.refresh_from_db()
        assert product.id != new_data["id"]
        assert list(str(team.id) for team in product.teams.all()) == []

    # delete
    def test_admin_can_delete_product(self, admin_client):
        product = ProductFactory()
        res = admin_client.delete(f"/api/products/{product.id}/")
        assert res.status_code == 204
        assert not Product.objects.filter(id=product.id).exists()

    def test_manager_can_delete_product(self, manager_client):
        product = ProductFactory()
        res = manager_client.delete(f"/api/products/{product.id}/")
        assert res.status_code == 204
        assert not Product.objects.filter(id=product.id).exists()

    def test_delete_product_archives_related_pipelines_deals_and_activities(self, admin_client):
        product = ProductFactory()
        pipeline = PipelineFactory(product=product)
        deal = DealFactory(pipeline=pipeline, assigned_to=pipeline.assigned_to)
        activity = ActivityFactory(deal=deal, assigned_to=pipeline.assigned_to)

        admin_client.delete(f"/api/products/{product.id}/")

        pipeline.refresh_from_db()
        assert pipeline.archived is not None
        deal.refresh_from_db()
        assert deal.archived is not None
        activity.refresh_from_db()
        assert activity.archived is not None

        # додаткова перевірка, що всі дані є в одній архівації
        assert pipeline.archived == deal.archived == activity.archived

        # перевірка типу архівації
        assert pipeline.archived.archiving_type == ArchivingType.PRODUCT_DELETED

    def test_sales_rep_cannot_delete_product(self, sales_rep_client):
        product = ProductFactory()
        res = sales_rep_client.delete(f"/api/products/{product.id}/")
        assert res.status_code == 403

    def test_employee_cannot_delete_product(self, employee_client):
        product = ProductFactory()
        res = employee_client.delete(f"/api/products/{product.id}/")
        assert res.status_code == 403
