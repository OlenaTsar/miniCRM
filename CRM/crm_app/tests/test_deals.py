from datetime import timedelta

import pytest
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .factories import (PipelineFactory,
                        ContactFactory,
                        ArchiveFactory,
                        DealFactory,
                        CompanyFactory,
                        ProductFactory,
                        ActivityFactory)
from crm_app.models import PipelineStage, DealStatus, Currency, Deal, Notification
from auth_app.tests.factories import UserFactory


@pytest.mark.django_db
class TestDealsEndpoint:
    # /api/deals/
    # GET
    def test_admin_can_list_deals(self, admin_client):
        DealFactory.create_batch(3)
        res = admin_client.get("/api/deals/")
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_manager_can_list_only_team_deals(self, manager_client, manager_user):
        # users з тієї самої команди
        team_users = UserFactory.create_batch(3, team=manager_user.team)
        # users з іншої команди
        other_users = UserFactory.create_batch(3)

        team_deals = []

        for user in team_users:
            team_deals.append(DealFactory(assigned_to=user))

        for user in other_users:
            DealFactory(assigned_to=user)

        res = manager_client.get("/api/deals/")
        assert res.status_code == 200
        assert len(res.data) == 3

        # список з id, які повинні повернутись
        deals_ids = [str(deal.id) for deal in team_deals]

        for deal_data in res.data:
            assert deal_data["id"] in deals_ids

    def test_sales_rep_can_list_only_own_deals(self, sales_rep_client, sales_rep_user):
        other_users = UserFactory.create_batch(3)

        sales_rep_deals = DealFactory.create_batch(2, assigned_to=sales_rep_user)

        for user in other_users:
            DealFactory(assigned_to=user)

        res = sales_rep_client.get("/api/deals/")
        assert res.status_code == 200
        assert len(res.data) == 2

        # список з id, які повинні повернутись
        deals_ids = [str(deal.id) for deal in sales_rep_deals]

        for deal_data in res.data:
            assert deal_data["id"] in deals_ids

    def test_employee_cannot_list_deals(self, employee_client):
        DealFactory.create_batch(3)
        res = employee_client.get("/api/deals/")
        assert res.status_code == 403

    def test_list_response_fields(self, admin_client):
        deal = DealFactory()
        res = admin_client.get(f"/api/deals/")

        deal_data = res.data[0]
        assert deal_data["id"] == str(deal.id)
        assert deal_data["name"] == deal.name
        assert deal_data["description"] == deal.description
        assert deal_data["status"] == deal.status
        assert float(deal_data["amount"]) == float(deal.amount)
        assert deal_data["currency"] == deal.currency
        if deal.expected_close_date is not None:
            assert parse_datetime(deal_data["expected_close_date"]) == deal.expected_close_date
        else:
            assert deal_data["expected_close_date"] is None
        assert parse_datetime(deal_data["created_at"]) == deal.created_at
        assert deal_data["stage"] == deal.stage
        if deal.closed_at is not None:
            assert parse_datetime(deal_data["closed_at"]) == deal.closed_at
        else:
            assert deal_data["closed_at"] is None
        assert deal_data["pipeline"] == deal.pipeline.id
        assert deal_data["product"] == deal.product.id
        assert deal_data["contact"] == deal.contact.id
        if deal.company is not None:
            assert deal_data["company"] == deal.company.id
        else:
            assert deal_data["company"] is None
        assert deal_data["assigned_to"] == deal.assigned_to.id
        assert (list(str(activity_id) for activity_id in deal_data["activities"]) ==
                list(str(activity.id) for activity in deal.activities.all()))

    def test_list_deals_display_archived(self, admin_client):
        deals = DealFactory.create_batch(3)
        archive = ArchiveFactory()
        archived_deals = DealFactory.create_batch(3, archived=archive)

        # при звичайному запиті архівований вміст не повертається
        res = admin_client.get("/api/deals/")
        assert res.status_code == 200
        assert len(res.data) == 3
        deal_ids = [str(deal.id) for deal in deals]

        for deal_data in res.data:
            assert deal_data["id"] in deal_ids

        # при display_archived=true архівований вміст повертається
        res = admin_client.get("/api/deals/", query_params={"display_archived": "true"})
        assert res.status_code == 200
        assert len(res.data) == 6
        deal_ids.extend([str(deal.id) for deal in archived_deals])

        for deal_data in res.data:
            assert deal_data["id"] in deal_ids

    # POST
    def test_admin_can_create_deal(self, admin_client, admin_user):
        pipeline = PipelineFactory(assigned_to=admin_user)
        contact = ContactFactory()
        data = {
            "name": "Test",
            "amount": 5000,
            "pipeline": pipeline.id,
            "contact": contact.id,
        }
        res = admin_client.post("/api/deals/", data=data, format="json")
        assert res.status_code == 201

        deal = Deal.objects.get(id=res.data["id"])
        assert deal.name == "Test"
        assert deal.assigned_to == admin_user

    def test_admin_can_create_deal_assigned_to_other_user(self, admin_client):
        user = UserFactory()
        pipeline = PipelineFactory(assigned_to=user)
        contact = ContactFactory()
        data = {
            "name": "Test",
            "amount": 5000,
            "pipeline": pipeline.id,
            "contact": contact.id,
        }
        res = admin_client.post("/api/deals/", data=data, format="json")
        assert res.status_code == 201

        deal = Deal.objects.get(id=res.data["id"])
        assert deal.name == "Test"
        assert deal.assigned_to == user

    def test_manager_can_create_deal(self, manager_client, manager_user):
        pipeline = PipelineFactory(assigned_to=manager_user)
        contact = ContactFactory()
        data = {
            "name": "Test",
            "amount": 5000,
            "pipeline": pipeline.id,
            "contact": contact.id,
        }
        res = manager_client.post("/api/deals/", data=data, format="json")
        assert res.status_code == 201

        deal = Deal.objects.get(id=res.data["id"])
        assert deal.name == "Test"
        assert deal.assigned_to == manager_user

    def test_manager_can_create_deal_assigned_to_team_user(self, manager_client, manager_user):
        user = UserFactory(team=manager_user.team)
        pipeline = PipelineFactory(assigned_to=user)
        contact = ContactFactory()
        data = {
            "name": "Test",
            "amount": 5000,
            "pipeline": pipeline.id,
            "contact": contact.id,
        }
        res = manager_client.post("/api/deals/", data=data, format="json")
        assert res.status_code == 201

        deal = Deal.objects.get(id=res.data["id"])
        assert deal.name == "Test"
        assert deal.assigned_to == user

    def test_manager_cannot_create_deal_assigned_to_not_team_user(self, manager_client, manager_user):
        pipeline = PipelineFactory()
        contact = ContactFactory()
        data = {
            "name": "Test",
            "amount": 5000,
            "pipeline": pipeline.id,
            "contact": contact.id,
        }
        res = manager_client.post("/api/deals/", data=data, format="json")
        assert res.status_code == 400

    def test_sales_rep_can_create_deal(self, sales_rep_client, sales_rep_user):
        pipeline = PipelineFactory(assigned_to=sales_rep_user)
        contact = ContactFactory()
        data = {
            "name": "Test",
            "amount": 5000,
            "pipeline": pipeline.id,
            "contact": contact.id,
        }
        res = sales_rep_client.post("/api/deals/", data=data, format="json")
        assert res.status_code == 201

        deal = Deal.objects.get(id=res.data["id"])
        assert deal.name == "Test"
        assert deal.assigned_to == sales_rep_user

    def test_sales_rep_cannot_create_deal_assigned_to_other_user(self, sales_rep_client):
        pipeline = PipelineFactory()
        contact = ContactFactory()
        data = {
            "name": "Test",
            "amount": 5000,
            "pipeline": pipeline.id,
            "contact": contact.id,
        }
        res = sales_rep_client.post("/api/deals/", data=data, format="json")
        assert res.status_code == 400

    def test_employee_cannot_create_deal(self, employee_client):
        pipeline = PipelineFactory()
        contact = ContactFactory()
        data = {
            "name": "Test",
            "amount": 5000,
            "pipeline": pipeline.id,
            "contact": contact.id,
        }
        res = employee_client.post("/api/deals/", data=data, format="json")
        assert res.status_code == 403

    def test_deal_product_matches_pipeline_product(self, admin_client):
        # перевіряє, чи при створенні угоди автоматично заповнюється поле product відповідно до pipeline
        pipeline = PipelineFactory()
        contact = ContactFactory()
        data = {
            "name": "Test",
            "amount": 5000,
            "pipeline": pipeline.id,
            "contact": contact.id,
        }
        res = admin_client.post("/api/deals/", data=data, format="json")

        deal = Deal.objects.get(id=res.data["id"])
        assert deal.product == pipeline.product

    def test_deal_assigned_to_matches_pipeline_assigned_to(self, admin_client):
        # неможливо передати assigned_to при створенні
        # при створенні угоди воно автоматично заповнюється відповідно до pipeline
        pipeline = PipelineFactory()
        contact = ContactFactory()
        user = UserFactory()
        data = {
            "name": "Test",
            "amount": 5000,
            "pipeline": pipeline.id,
            "contact": contact.id,
            "assigned_to": user.id,
        }
        res = admin_client.post("/api/deals/", data=data, format="json")

        deal = Deal.objects.get(id=res.data["id"])
        assert deal.assigned_to == pipeline.assigned_to

    def test_create_deal_without_required_fields_fails(self, admin_client):
        res = admin_client.post("/api/deals/")

        assert res.status_code == 400
        assert "name" in res.data
        assert "amount" in res.data
        assert "pipeline" in res.data
        assert "contact" in res.data

    # /api/deals/{deal-id}/
    # retrieve
    def test_admin_can_retrieve_deal(self, admin_client):
        deal = DealFactory()
        res = admin_client.get(f"/api/deals/{deal.id}/")
        assert res.status_code == 200

    def test_manager_can_retrieve_team_deal(self, manager_client, manager_user):
        user = UserFactory(team=manager_user.team)
        deal = DealFactory(assigned_to=user)

        res = manager_client.get(f"/api/deals/{deal.id}/")
        assert res.status_code == 200

    def test_manager_cannot_retrieve_not_team_deal(self, manager_client):
        deal = DealFactory()

        res = manager_client.get(f"/api/deals/{deal.id}/")
        assert res.status_code == 404

    def test_sales_rep_can_retrieve_own_deal(self, sales_rep_client, sales_rep_user):
        deal = DealFactory(assigned_to=sales_rep_user)

        res = sales_rep_client.get(f"/api/deals/{deal.id}/")
        assert res.status_code == 200

    def test_sales_rep_cannot_retrieve_other_user_deal(self, sales_rep_client):
        deal = DealFactory()

        res = sales_rep_client.get(f"/api/deals/{deal.id}/")
        assert res.status_code == 404

    def test_employee_cannot_retrieve_deal(self, employee_client):
        deal = DealFactory()

        res = employee_client.get(f"/api/deals/{deal.id}/")
        assert res.status_code == 403

    def test_retrieve_deal_display_archived(self, admin_client):
        archive = ArchiveFactory()
        archived_deal = DealFactory(archived=archive)

        # при звичайному запиті архівований вміст не повертається
        res = admin_client.get(f"/api/deals/{archived_deal.id}/")
        assert res.status_code == 404

        # при display_archived=true архівований вміст повертається
        res = admin_client.get(f"/api/deals/{archived_deal.id}/", query_params={"display_archived": "true"})
        assert res.status_code == 200

    # partial_update
    def test_admin_can_update_deal(self, admin_client):
        # тут тестується зміна усіх полів, окрім pipeline та assigned_to
        deal = DealFactory()
        new_data = {
            "name": "New Name",
            "description": "New description",
            "amount": 3600,
            "currency": Currency.EUR,
            "expected_close_date": timezone.now() + timedelta(days=10),
            "company": CompanyFactory().id,
        }
        res = admin_client.patch(f"/api/deals/{deal.id}/", data=new_data, format="json")
        assert res.status_code == 200

        deal.refresh_from_db()
        assert new_data["name"] == deal.name
        assert new_data["description"] == deal.description
        assert float(new_data["amount"]) == float(deal.amount)
        assert new_data["currency"] == deal.currency
        assert new_data["expected_close_date"] == deal.expected_close_date
        assert new_data["company"] == deal.company.id

    def test_admin_can_move_deal_to_another_pipeline_of_same_user(self, admin_client):
        # угода переноситься в іншу pipeline того ж самого користувача
        # product є однаковим для обох pipeline
        user = UserFactory()
        product = ProductFactory()
        pipeline1, pipeline2 = PipelineFactory.create_batch(2, assigned_to=user, product=product)
        deal = DealFactory(pipeline=pipeline1)

        res = admin_client.patch(f"/api/deals/{deal.id}/", data={'pipeline': pipeline2.id}, format="json")

        assert res.status_code == 200
        deal.refresh_from_db()
        assert deal.pipeline == pipeline2

    def test_admin_can_move_deal_to_pipeline_of_another_user(self, admin_client):
        # угода переноситься в іншу pipeline іншого користувача
        # product є однаковим для обох pipeline
        user1, user2 = UserFactory.create_batch(2)
        product = ProductFactory()
        pipeline1 = PipelineFactory(assigned_to=user1, product=product)
        pipeline2 = PipelineFactory(assigned_to=user2, product=product)
        deal = DealFactory(pipeline=pipeline1)

        res = admin_client.patch(f"/api/deals/{deal.id}/", data={'pipeline': pipeline2.id}, format="json")

        assert res.status_code == 200
        deal.refresh_from_db()
        assert deal.pipeline == pipeline2
        assert deal.assigned_to == user2

    def test_move_deal_to_pipeline_with_different_product_fails(self, admin_client):
        # перевіряє, чи повертає помилку, якщо нова pipeline відповідає за інший product
        pipeline1, pipeline2 = PipelineFactory.create_batch(2)
        deal = DealFactory(pipeline=pipeline1)

        res = admin_client.patch(f"/api/deals/{deal.id}/", data={'pipeline': pipeline2.id}, format="json")

        assert res.status_code == 400
        deal.refresh_from_db()
        assert deal.pipeline == pipeline1

    def test_move_archived_deal_to_not_archived_pipeline_success(self, admin_client):
        # якщо стара pipeline є архівованою, угода повинна перенестись успішно
        # якщо угода є архівованою - вона повинна перенестись успішно
        product = ProductFactory()
        pipeline1, pipeline2 = PipelineFactory.create_batch(2, product=product)
        deal = DealFactory(pipeline=pipeline1)

        archive = ArchiveFactory()
        pipeline1.archived = archive
        pipeline1.save()  # угода архівується автоматично

        res = admin_client.patch(f"/api/deals/{deal.id}/",
                                 data={'pipeline': pipeline2.id},
                                 format="json",
                                 query_params={"display_archived": "true"})

        assert res.status_code == 200
        deal.refresh_from_db()
        assert deal.pipeline == pipeline2

    def test_move_deal_to_archived_pipeline_fails(self, admin_client):
        # якщо нова pipeline є архівованою, повинна повернутись помилка
        product = ProductFactory()
        pipeline1, pipeline2 = PipelineFactory.create_batch(2, product=product)
        deal = DealFactory(pipeline=pipeline1)

        archive = ArchiveFactory()
        pipeline2.archived = archive
        pipeline2.save()

        res = admin_client.patch(f"/api/deals/{deal.id}/", data={'pipeline': pipeline2.id}, format="json")

        assert res.status_code == 400
        deal.refresh_from_db()
        assert deal.pipeline == pipeline1

    def test_update_deal_fails_when_assigned_to_does_not_match_pipeline(self, admin_client):
        # при спробі одночасно змінити assigned_to та pipeline виникне помилка,
        # у випадку коли pipeline.assigned_to не збігається з assigned_to
        product = ProductFactory()
        user = UserFactory()
        pipeline1, pipeline2 = PipelineFactory.create_batch(2, product=product)
        deal = DealFactory(pipeline=pipeline1)
        data = {
            'pipeline': pipeline2.id,
            'assigned_to': user.id,
        }

        res = admin_client.patch(f"/api/deals/{deal.id}/", data=data, format="json")

        assert res.status_code == 400
        deal.refresh_from_db()
        assert deal.pipeline == pipeline1
        assert deal.assigned_to == pipeline1.assigned_to

    def test_admin_can_update_deal_change_assigned_to(self, admin_client):
        # зміна assigned_to у випадку, коли новий користувач має pipeline, яка відповідає за продукт угоди
        user1, user2 = UserFactory.create_batch(2)
        product = ProductFactory()
        pipeline1 = PipelineFactory(assigned_to=user1, product=product)
        pipeline2 = PipelineFactory(assigned_to=user2, product=product)
        deal = DealFactory(pipeline=pipeline1)

        res = admin_client.patch(f"/api/deals/{deal.id}/", data={'assigned_to': user2.id}, format="json")

        assert res.status_code == 200
        deal.refresh_from_db()
        assert deal.pipeline == pipeline2
        assert deal.assigned_to == user2

    def test_change_deal_assigned_to_fails_when_new_user_has_no_pipeline_for_deal_product(self, admin_client):
        # зміна assigned_to у випадку, коли новий користувач не має pipeline, яка відповідає за продукт угоди
        # або має відповідну pipeline, але вона є заархівованою

        user1, user2 = UserFactory.create_batch(2)
        user1_pipeline1 = PipelineFactory(assigned_to=user1)
        deal = DealFactory(pipeline=user1_pipeline1)

        # user2 буде мати pipeline, але з іншим product
        user2_pipeline1 = PipelineFactory(assigned_to=user2)
        # заархівована pipeline з тим самим product, що і угода
        user2_pipeline2 = PipelineFactory(assigned_to=user2, product=deal.product)
        archive = ArchiveFactory()
        user2_pipeline2.archived = archive
        user2_pipeline2.save()

        res = admin_client.patch(f"/api/deals/{deal.id}/", data={'assigned_to': user2.id}, format="json")

        assert res.status_code == 400
        deal.refresh_from_db()
        assert deal.pipeline == user1_pipeline1
        assert deal.assigned_to == user1

    def test_manager_can_update_team_deal(self, manager_client, manager_user):
        # менеджер може змінити угоду користувача своєї команди
        # тут тестується зміна усіх полів, окрім pipeline та assigned_to
        user = UserFactory(team=manager_user.team)
        pipeline = PipelineFactory(assigned_to=user)
        deal = DealFactory(pipeline=pipeline)

        new_data = {
            "name": "New Name",
            "description": "New description",
            "amount": 3600,
            "currency": Currency.EUR,
            "expected_close_date": timezone.now() + timedelta(days=10),
            "company": CompanyFactory().id,
        }
        res = manager_client.patch(f"/api/deals/{deal.id}/", data=new_data, format="json")
        assert res.status_code == 200

        deal.refresh_from_db()
        assert new_data["name"] == deal.name
        assert new_data["description"] == deal.description
        assert float(new_data["amount"]) == float(deal.amount)
        assert new_data["currency"] == deal.currency
        assert new_data["expected_close_date"] == deal.expected_close_date
        assert new_data["company"] == deal.company.id

    def test_manager_cannot_update_not_team_deal(self, manager_client):
        # менеджер не може змінити угоду користувача не своєї команди
        deal = DealFactory()
        res = manager_client.patch(f"/api/deals/{deal.id}/")
        assert res.status_code == 404

    def test_manager_can_move_team_deal_to_team_user_pipeline(self, manager_client, manager_user):
        # менеджер може перенести угоду в pipeline користувача своєї команди
        # при умові, що нова pipeline відповідає за той самий продукт
        user1 = UserFactory(team=manager_user.team)
        user2 = UserFactory(team=manager_user.team)

        product = ProductFactory()
        pipeline_user1 = PipelineFactory(assigned_to=user1, product=product)
        pipeline_user2 = PipelineFactory(assigned_to=user2, product=product)
        deal = DealFactory(pipeline=pipeline_user1)

        res = manager_client.patch(f"/api/deals/{deal.id}/", data={"pipeline": pipeline_user2.id}, format="json")
        assert res.status_code == 200

        deal.refresh_from_db()
        assert deal.pipeline == pipeline_user2
        assert deal.assigned_to == user2

    def test_manager_can_not_move_team_deal_to_not_team_user_pipeline(self, manager_client, manager_user):
        # менеджер не може перенести угоду в pipeline користувача не своєї команди
        user1 = UserFactory(team=manager_user.team)
        user2 = UserFactory()

        product = ProductFactory()
        pipeline_user1 = PipelineFactory(assigned_to=user1, product=product)
        pipeline_user2 = PipelineFactory(assigned_to=user2, product=product)
        deal = DealFactory(pipeline=pipeline_user1)

        res = manager_client.patch(f"/api/deals/{deal.id}/", data={"pipeline": pipeline_user2.id}, format="json")
        assert res.status_code == 403

        deal.refresh_from_db()
        assert deal.pipeline == pipeline_user1
        assert deal.assigned_to == user1

    def test_manager_can_change_deal_assignee_to_user_from_same_team(self, manager_client, manager_user):
        # менеджер може передати угоду користувачеві своєї команди
        # при умові, що в нового користувача є pipeline, яка відповідає за той самий продукт
        user1 = UserFactory(team=manager_user.team)
        user2 = UserFactory(team=manager_user.team)

        product = ProductFactory()
        pipeline_user1 = PipelineFactory(assigned_to=user1, product=product)
        pipeline_user2 = PipelineFactory(assigned_to=user2, product=product)
        deal = DealFactory(pipeline=pipeline_user1)

        res = manager_client.patch(f"/api/deals/{deal.id}/", data={"assigned_to": user2.id}, format="json")
        assert res.status_code == 200

        deal.refresh_from_db()
        assert deal.pipeline == pipeline_user2
        assert deal.assigned_to == user2

    def test_manager_cannot_change_deal_assignee_to_user_from_another_team(self, manager_client, manager_user):
        # менеджер не може передати угоду користувачеві не своєї команди
        user1 = UserFactory(team=manager_user.team)
        user2 = UserFactory()

        product = ProductFactory()
        pipeline_user1 = PipelineFactory(assigned_to=user1, product=product)
        pipeline_user2 = PipelineFactory(assigned_to=user2, product=product)
        deal = DealFactory(pipeline=pipeline_user1)

        res = manager_client.patch(f"/api/deals/{deal.id}/", data={"assigned_to": user2.id}, format="json")
        assert res.status_code == 403

        deal.refresh_from_db()
        assert deal.pipeline == pipeline_user1
        assert deal.assigned_to == user1

    def test_sales_rep_can_update_own_deal(self, sales_rep_client, sales_rep_user):
        # sales_rep може змінити свою угоду
        # тут тестується зміна усіх полів, окрім pipeline та assigned_to
        pipeline = PipelineFactory(assigned_to=sales_rep_user)
        deal = DealFactory(pipeline=pipeline)

        new_data = {
            "name": "New Name",
            "description": "New description",
            "amount": 3600,
            "currency": Currency.EUR,
            "expected_close_date": timezone.now() + timedelta(days=10),
            "company": CompanyFactory().id,
        }
        res = sales_rep_client.patch(f"/api/deals/{deal.id}/", data=new_data, format="json")
        assert res.status_code == 200

        deal.refresh_from_db()
        assert new_data["name"] == deal.name
        assert new_data["description"] == deal.description
        assert float(new_data["amount"]) == float(deal.amount)
        assert new_data["currency"] == deal.currency
        assert new_data["expected_close_date"] == deal.expected_close_date
        assert new_data["company"] == deal.company.id

    def test_sales_rep_cannot_update_other_user_deal(self, sales_rep_client):
        # sales_rep не може змінити не свою угоду
        deal = DealFactory()
        res = sales_rep_client.patch(f"/api/deals/{deal.id}/")
        assert res.status_code == 404

    def test_sales_rep_can_move_own_deal_to_own_pipeline(self, sales_rep_client, sales_rep_user):
        # sales_rep може переміщати угоди між своїми pipeline
        product = ProductFactory()
        pipeline1 = PipelineFactory(assigned_to=sales_rep_user, product=product)
        pipeline2 = PipelineFactory(assigned_to=sales_rep_user, product=product)
        deal = DealFactory(pipeline=pipeline1)

        res = sales_rep_client.patch(f"/api/deals/{deal.id}/", data={'pipeline': pipeline2.id}, format="json")
        assert res.status_code == 200

        deal.refresh_from_db()
        deal.pipeline = pipeline2

    def test_sales_rep_cannot_move_own_deal_to_not_own_pipeline(self, sales_rep_client, sales_rep_user):
        # sales_rep не може перемістити угоду в чужу pipeline
        product = ProductFactory()
        pipeline1 = PipelineFactory(assigned_to=sales_rep_user, product=product)
        pipeline2 = PipelineFactory(product=product)
        deal = DealFactory(pipeline=pipeline1)

        res = sales_rep_client.patch(f"/api/deals/{deal.id}/", data={'pipeline': pipeline2.id}, format="json")
        assert res.status_code == 403

        deal.refresh_from_db()
        deal.pipeline = pipeline1

    def test_sales_rep_cannot_change_deal_assignee(self, sales_rep_client, sales_rep_user):
        # sales_rep не може призначити угоду іншому користувачеві
        product = ProductFactory()
        pipeline1 = PipelineFactory(assigned_to=sales_rep_user, product=product)
        deal = DealFactory(pipeline=pipeline1)

        user = UserFactory()
        pipeline2 = PipelineFactory(product=product, assigned_to=user)

        res = sales_rep_client.patch(f"/api/deals/{deal.id}/", data={'assigned_to': user.id}, format="json")
        assert res.status_code == 400

        deal.refresh_from_db()
        deal.assignee_to = sales_rep_user

    def test_employee_cannot_update_deal(self, employee_client):
        deal = DealFactory()
        res = employee_client.patch(f"/api/deals/{deal.id}/")
        assert res.status_code == 403

    def test_change_deal_assignee_cascades_to_activities(self, admin_client):
        # перевіряє, що зміна assigned_to в deal поширюється на activities, які належать цьому deal
        deal = DealFactory()
        activities = ActivityFactory.create_batch(4, deal=deal)
        user = UserFactory()
        new_data = {
            "assigned_to": user.id,
        }

        res = admin_client.patch(f"/api/deals/{deal.id}/", data=new_data, format="json")

        assert res.status_code == 200

        deal.refresh_from_db()
        assert deal.assigned_to == user

        for activity in activities:
            activity.refresh_from_db()
            assert activity.assigned_to == user

    # delete
    def test_admin_can_delete_deal(self, admin_client):
        deal = DealFactory()
        res = admin_client.delete(f"/api/deals/{deal.id}/")
        assert res.status_code == 204
        assert not Deal.objects.filter(id=deal.id).exists()

    def test_manager_can_delete_team_deal(self, manager_client, manager_user):
        user = UserFactory(team=manager_user.team)
        deal = DealFactory(assigned_to=user)

        res = manager_client.delete(f"/api/deals/{deal.id}/")

        assert res.status_code == 204
        assert not Deal.objects.filter(id=deal.id).exists()

    def test_manager_cannot_delete_not_team_deal(self, manager_client):
        deal = DealFactory()

        res = manager_client.delete(f"/api/deals/{deal.id}/")

        assert res.status_code == 404
        assert Deal.objects.filter(id=deal.id).exists()

    def test_sales_rep_can_delete_own_deal(self, sales_rep_client, sales_rep_user):
        deal = DealFactory(assigned_to=sales_rep_user)

        res = sales_rep_client.delete(f"/api/deals/{deal.id}/")

        assert res.status_code == 204
        assert not Deal.objects.filter(id=deal.id).exists()

    def test_sales_rep_cannot_delete_not_own_deal(self, sales_rep_client):
        deal = DealFactory()

        res = sales_rep_client.delete(f"/api/deals/{deal.id}/")

        assert res.status_code == 404
        assert Deal.objects.filter(id=deal.id).exists()

    def test_employee_cannot_delete_deal(self, employee_client):
        deal = DealFactory()

        res = employee_client.delete(f"/api/deals/{deal.id}/")

        assert res.status_code == 403


@pytest.mark.django_db
class TestDealsChangeStageEndpoint:
    # /api/deals/{id}/change-stage/
    # POST

    def test_admin_can_change_deal_stage(self, admin_client):
        deal = DealFactory()

        res = admin_client.post(f"/api/deals/{deal.id}/change-stage/",
                                data={'stage': PipelineStage.QUALIFICATION},
                                format="json")

        assert res.status_code == 200

        deal.refresh_from_db()
        assert deal.stage == PipelineStage.QUALIFICATION

    def test_manager_can_change_stage_of_deal_assigned_to_user_from_same_team(self, manager_client, manager_user):
        # manager може змінити stage угоди користувача зі своєї команди
        user = UserFactory(team=manager_user.team)
        deal = DealFactory(assigned_to=user)

        res = manager_client.post(f"/api/deals/{deal.id}/change-stage/",
                                  data={'stage': PipelineStage.QUALIFICATION},
                                  format="json")

        assert res.status_code == 200

        deal.refresh_from_db()
        assert deal.stage == PipelineStage.QUALIFICATION

    def test_manager_cannot_change_stage_of_deal_assigned_to_user_from_another_team(self, manager_client):
        deal = DealFactory()

        res = manager_client.post(f"/api/deals/{deal.id}/change-stage/",
                                  data={'stage': PipelineStage.QUALIFICATION},
                                  format="json")

        assert res.status_code == 404

        deal.refresh_from_db()
        assert deal.stage == PipelineStage.NEW_LEAD

    def test_sales_rep_can_change_stage_of_own_deal(self, sales_rep_client, sales_rep_user):
        deal = DealFactory(assigned_to=sales_rep_user)

        res = sales_rep_client.post(f"/api/deals/{deal.id}/change-stage/",
                                    data={'stage': PipelineStage.QUALIFICATION},
                                    format="json")

        assert res.status_code == 200

        deal.refresh_from_db()
        assert deal.stage == PipelineStage.QUALIFICATION

    def test_sales_rep_cannot_change_stage_of_deal_assigned_to_other_user(self, sales_rep_client):
        deal = DealFactory()

        res = sales_rep_client.post(f"/api/deals/{deal.id}/change-stage/",
                                    data={'stage': PipelineStage.QUALIFICATION},
                                    format="json")

        assert res.status_code == 404

        deal.refresh_from_db()
        assert deal.stage == PipelineStage.NEW_LEAD

    def test_change_deal_stage_updates_deal_status(self, admin_client):
        # при зміні stage змінюється deal status, відповідно до нового stage

        #  PipelineStage ----- DealStatus
        #
        #  New Lead ----- New
        #  Qualification ----- In Progress
        #  Proposal Sent ----- In Progress
        #  Negotiation ----- In Progress
        #  Closed Won ----- Closed
        #  Closed Lost ----- Closed

        deal = DealFactory()

        admin_client.post(f"/api/deals/{deal.id}/change-stage/",
                          data={'stage': PipelineStage.QUALIFICATION},
                          format="json")

        deal.refresh_from_db()
        assert deal.status == DealStatus.IN_PROGRESS

        admin_client.post(f"/api/deals/{deal.id}/change-stage/",
                          data={'stage': PipelineStage.PROPOSAL_SENT},
                          format="json")

        deal.refresh_from_db()
        assert deal.status == DealStatus.IN_PROGRESS

        admin_client.post(f"/api/deals/{deal.id}/change-stage/",
                          data={'stage': PipelineStage.NEGOTIATION},
                          format="json")

        deal.refresh_from_db()
        assert deal.status == DealStatus.IN_PROGRESS

        admin_client.post(f"/api/deals/{deal.id}/change-stage/",
                          data={'stage': PipelineStage.NEW_LEAD},
                          format="json")

        deal.refresh_from_db()
        assert deal.status == DealStatus.NEW

        admin_client.post(f"/api/deals/{deal.id}/change-stage/",
                          data={'stage': PipelineStage.CLOSED_WON},
                          format="json")

        deal.refresh_from_db()
        assert deal.status == DealStatus.CLOSED

        deal2 = DealFactory()

        admin_client.post(f"/api/deals/{deal2.id}/change-stage/",
                          data={'stage': PipelineStage.CLOSED_LOST},
                          format="json")

        deal2.refresh_from_db()
        assert deal2.status == DealStatus.CLOSED

    def test_change_stage_of_closed_deal_fails(self, admin_client):
        # Неможливо змінити stage завершеної угоди
        deal = DealFactory(stage=PipelineStage.CLOSED_WON, status=DealStatus.CLOSED, closed_at=timezone.now())

        res = admin_client.post(f"/api/deals/{deal.id}/change-stage/",
                                data={'stage': PipelineStage.NEGOTIATION},
                                format="json")

        assert res.status_code == 400

        deal.refresh_from_db()
        assert deal.stage == PipelineStage.CLOSED_WON

    def test_change_stage_of_deal_on_hold_fails(self, admin_client):
        # Неможливо змінити stage угоди, яка на паузі
        deal = DealFactory(status=DealStatus.ON_HOLD)

        res = admin_client.post(f"/api/deals/{deal.id}/change-stage/",
                                data={'stage': PipelineStage.NEGOTIATION},
                                format="json")

        assert res.status_code == 400

        deal.refresh_from_db()
        assert deal.stage == PipelineStage.NEW_LEAD

    def test_closing_deal_sets_closed_at(self, admin_client):
        # якщо угода завершена, автоматично має заповнитись deal.closed_at
        deal = DealFactory()

        res = admin_client.post(f"/api/deals/{deal.id}/change-stage/",
                                data={'stage': PipelineStage.CLOSED_WON},
                                format="json")

        deal.refresh_from_db()
        assert deal.closed_at is not None

    def test_unsent_notification_is_deleted_when_deal_is_closed(self, admin_client):
        # сповіщення для активності завершеної угоди автоматично видаляється, якщо воно ще не було надіслано
        deal = DealFactory()
        activity = ActivityFactory(deal=deal)

        res = admin_client.post(f"/api/deals/{deal.id}/change-stage/",
                                data={'stage': PipelineStage.CLOSED_WON},
                                format="json")

        assert not Notification.objects.filter(activity=activity).exists()


@pytest.mark.django_db
class TestDealsHoldEndpoint:
    # /api/deals/{id}/hold/
    # POST

    def test_admin_can_set_deal_on_hold(self, admin_client):
        deal = DealFactory()

        res = admin_client.post(f"/api/deals/{deal.id}/hold/")

        assert res.status_code == 200
        deal.refresh_from_db()
        assert deal.status == DealStatus.ON_HOLD

    def test_admin_can_resume_deal(self, admin_client):
        deal = DealFactory(status=DealStatus.ON_HOLD)

        res = admin_client.post(f"/api/deals/{deal.id}/hold/")

        assert res.status_code == 200
        deal.refresh_from_db()
        assert deal.status == DealStatus.NEW

    def test_manager_can_set_deal_on_hold_for_user_from_same_team(self, manager_client, manager_user):
        user = UserFactory(team=manager_user.team)
        deal = DealFactory(assigned_to=user)

        res = manager_client.post(f"/api/deals/{deal.id}/hold/")

        assert res.status_code == 200
        deal.refresh_from_db()
        assert deal.status == DealStatus.ON_HOLD

    def test_manager_can_resume_deal_for_user_from_same_team(self, manager_client, manager_user):
        user = UserFactory(team=manager_user.team)
        deal = DealFactory(assigned_to=user, status=DealStatus.ON_HOLD)

        res = manager_client.post(f"/api/deals/{deal.id}/hold/")

        assert res.status_code == 200
        deal.refresh_from_db()
        assert deal.status == DealStatus.NEW

    def test_manager_cannot_set_deal_on_hold_for_user_from_another_team(self, manager_client):
        deal = DealFactory()
        res = manager_client.post(f"/api/deals/{deal.id}/hold/")
        assert res.status_code == 404

    def test_sales_rep_can_set_own_deal_on_hold(self, sales_rep_client, sales_rep_user):
        deal = DealFactory(assigned_to=sales_rep_user)

        res = sales_rep_client.post(f"/api/deals/{deal.id}/hold/")

        assert res.status_code == 200
        deal.refresh_from_db()
        assert deal.status == DealStatus.ON_HOLD

    def test_sales_rep_can_resume_own_deal(self, sales_rep_client, sales_rep_user):
        deal = DealFactory(assigned_to=sales_rep_user, status=DealStatus.ON_HOLD)

        res = sales_rep_client.post(f"/api/deals/{deal.id}/hold/")

        assert res.status_code == 200
        deal.refresh_from_db()
        assert deal.status == DealStatus.NEW

    def test_sales_rep_cannot_set_deal_on_hold_for_another_user(self, sales_rep_client):
        deal = DealFactory()
        res = sales_rep_client.post(f"/api/deals/{deal.id}/hold/")
        assert res.status_code == 404

    def test_set_closed_deal_on_hold_fails(self, admin_client):
        # Неможливо змінити статус завершеної угоди
        deal = DealFactory(stage=PipelineStage.CLOSED_WON, status=DealStatus.CLOSED, closed_at=timezone.now())

        res = admin_client.post(f"/api/deals/{deal.id}/hold/")

        assert res.status_code == 400
        deal.refresh_from_db()
        assert deal.status == DealStatus.CLOSED

    def test_resume_deal_updates_status_according_to_stage(self, admin_client):
        # при знятті з паузи коректно змінюється deal status, відповідно до stage

        #  PipelineStage ----- DealStatus
        #
        #  New Lead ----- New
        #  Qualification ----- In Progress
        #  Proposal Sent ----- In Progress
        #  Negotiation ----- In Progress

        deal = DealFactory(stage=PipelineStage.NEW_LEAD, status=DealStatus.ON_HOLD)

        admin_client.post(f"/api/deals/{deal.id}/hold/")

        deal.refresh_from_db()
        assert deal.status == DealStatus.NEW

        deal = DealFactory(stage=PipelineStage.QUALIFICATION, status=DealStatus.ON_HOLD)

        admin_client.post(f"/api/deals/{deal.id}/hold/")

        deal.refresh_from_db()
        assert deal.status == DealStatus.IN_PROGRESS

        deal = DealFactory(stage=PipelineStage.PROPOSAL_SENT, status=DealStatus.ON_HOLD)

        admin_client.post(f"/api/deals/{deal.id}/hold/")

        deal.refresh_from_db()
        assert deal.status == DealStatus.IN_PROGRESS

        deal = DealFactory(stage=PipelineStage.NEGOTIATION, status=DealStatus.ON_HOLD)

        admin_client.post(f"/api/deals/{deal.id}/hold/")

        deal.refresh_from_db()
        assert deal.status == DealStatus.IN_PROGRESS

    def test_resume_deal_restores_notification_for_incomplete_non_overdue_activity(self, admin_client):
        # при знятті угоди з паузи відновлюється notification для activity, якщо вона не завершена і не є простроченою
        deal = DealFactory(status=DealStatus.ON_HOLD)
        activity_1 = ActivityFactory(deal=deal, due_date=timezone.now() + timedelta(minutes=30))
        activity_2 = ActivityFactory(deal=deal, due_date=timezone.now() + timedelta(hours=10))
        Notification.objects.filter(activity=activity_1).delete()
        Notification.objects.filter(activity=activity_2).delete()

        admin_client.post(f"/api/deals/{deal.id}/hold/")

        assert Notification.objects.filter(activity=activity_1).exists()
        assert Notification.objects.filter(activity=activity_2).exists()

        # якщо запланований час активності менше ніж через годину - сповіщення повинне прийти через хвилину
        assert activity_1.notification.notify_at <= timezone.now() + timedelta(minutes=1)

        # якщо запланований час активності більше ніж через годину -
        # сповіщення повинне прийти за годину до запланованого часу
        assert activity_2.notification.notify_at <= activity_2.due_date - timedelta(hours=1)

    def test_resume_deal_does_not_restore_notification_for_completed_activity(self, admin_client):
        # при знятті угоди з паузи не відновлюється notification для завершеної activity
        deal = DealFactory(status=DealStatus.ON_HOLD)
        activity = ActivityFactory(deal=deal, completed_at=timezone.now())
        Notification.objects.filter(activity=activity).delete()

        admin_client.post(f"/api/deals/{deal.id}/hold/")

        assert not Notification.objects.filter(activity=activity).exists()

    def test_resume_deal_does_not_restore_notification_for_overdue_activity(self, admin_client):
        # при знятті угоди з паузи не відновлюється notification для простроченої activity
        deal = DealFactory(status=DealStatus.ON_HOLD)
        activity = ActivityFactory(deal=deal, due_date=timezone.now())
        Notification.objects.filter(activity=activity).delete()

        admin_client.post(f"/api/deals/{deal.id}/hold/")

        assert not Notification.objects.filter(activity=activity).exists()

    def test_set_deal_on_hold_deletes_unsent_notification(self, admin_client):
        # при встановленні угоди на паузу, сповіщення видаляється, якщо воно ще не було надіслане
        deal = DealFactory()
        activity = ActivityFactory(deal=deal, due_date=timezone.now() + timedelta(hours=10))

        admin_client.post(f"/api/deals/{deal.id}/hold/")

        assert not Notification.objects.filter(activity=activity).exists()

    def test_set_deal_on_hold_does_not_delete_sent_notification(self, admin_client):
        # при встановленні угоди на паузу, надіслане сповіщення не видаляється
        deal = DealFactory()
        activity = ActivityFactory(deal=deal)
        notification = Notification.objects.get(activity=activity)
        notification.sent_at = timezone.now()
        notification.save()

        admin_client.post(f"/api/deals/{deal.id}/hold/")

        assert Notification.objects.filter(activity=activity).exists()


@pytest.mark.django_db
class TestDealsStageHistoryEndpoint:
    # /api/deals/{id}/stage-history/
    # GET

    def test_admin_can_list_deal_stage_history(self, admin_client, admin_user):
        deal = DealFactory()

        res = admin_client.get(f"/api/deals/{deal.id}/stage-history/")

        assert res.status_code == 200

    def test_deal_stage_history_data(self, admin_client, admin_user):
        deal = DealFactory()

        admin_client.post(f"/api/deals/{deal.id}/change-stage/",
                          data={'stage': PipelineStage.QUALIFICATION},
                          format="json")

        res = admin_client.get(f"/api/deals/{deal.id}/stage-history/")

        assert len(res.data) == 1

        stage_history = res.data[0]
        assert stage_history['old_stage'] == PipelineStage.NEW_LEAD
        assert stage_history['new_stage'] == PipelineStage.QUALIFICATION
        assert stage_history['changed_by'] == admin_user.email

    def test_manager_can_list_stage_history_of_deal_assigned_to_user_from_same_team(self, manager_client, manager_user):
        user = UserFactory(team=manager_user.team)
        deal = DealFactory(assigned_to=user)

        res = manager_client.get(f"/api/deals/{deal.id}/stage-history/")

        assert res.status_code == 200

    def test_manager_cannot_list_stage_history_of_deal_assigned_to_user_from_another_team(self, manager_client,
                                                                                          manager_user):
        deal = DealFactory()
        res = manager_client.get(f"/api/deals/{deal.id}/stage-history/")
        assert res.status_code == 404

    def test_sales_rep_can_list_stage_history_of_own_deal(self, sales_rep_client, sales_rep_user):
        deal = DealFactory(assigned_to=sales_rep_user)
        res = sales_rep_client.get(f"/api/deals/{deal.id}/stage-history/")
        assert res.status_code == 200

    def test_sales_rep_cannot_list_stage_history_of_deal_assigned_to_another_user(self, sales_rep_client,
                                                                                  sales_rep_user):
        deal = DealFactory()
        res = sales_rep_client.get(f"/api/deals/{deal.id}/stage-history/")
        assert res.status_code == 404
