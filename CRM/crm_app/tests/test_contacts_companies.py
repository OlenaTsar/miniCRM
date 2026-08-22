import pytest
from django.utils.dateparse import parse_datetime

from .factories import CompanyFactory, ContactFactory, DealFactory, ActivityFactory
from crm_app.models import Contact, Company, LeadSource, ContactStatus


@pytest.mark.django_db
class TestCompaniesEndpoint:
    # /api/companies/
    # GET
    def test_admin_can_list_companies(self, admin_client):
        CompanyFactory.create_batch(3)
        res = admin_client.get("/api/companies/")
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_manager_can_list_companies(self, manager_client):
        CompanyFactory.create_batch(3)
        res = manager_client.get("/api/companies/")
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_sales_rep_can_list_companies(self, sales_rep_client):
        CompanyFactory.create_batch(3)
        res = sales_rep_client.get("/api/companies/")
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_employee_cannot_list_companies(self, employee_client):
        CompanyFactory.create_batch(3)
        res = employee_client.get("/api/companies/")
        assert res.status_code == 403

    def test_unauthenticated_cannot_list_companies(self, api_client):
        CompanyFactory.create_batch(3)
        res = api_client.get("/api/companies/")
        assert res.status_code == 401

    def test_list_response_fields(self, admin_client):
        company = CompanyFactory()
        res = admin_client.get("/api/companies/")

        # перевіряємо, чи повернулися дані саме створеної company
        company_data = res.data[0]
        assert company_data["id"] == str(company.id)
        assert company_data["name"] == company.name
        assert company_data["description"] == company.description
        assert company_data["industry"] == company.industry
        assert company_data["website"] == company.website
        assert company_data["email"] == company.email
        assert company_data["instagram_url"] == company.instagram_url
        assert company_data["facebook_url"] == company.facebook_url
        assert parse_datetime(company_data["created_at"]) == company.created_at
        assert (list(str(contact_id) for contact_id in company_data["contacts"]) ==
                list(str(contact.id) for contact in company.contacts.all()))
        assert company_data["created_by"] == company.created_by.id
        assert (list(str(deal_id) for deal_id in company_data["deals"]) ==
                list(str(deal.id) for deal in company.deals.all()))

    # POST
    def test_admin_can_create_companies(self, admin_client, admin_user):
        res = admin_client.post("/api/companies/", data={"name": "Test"}, format="json")
        assert res.status_code == 201

        company = Company.objects.get(id=res.data["id"])
        assert company.name == "Test"
        assert company.created_by == admin_user

    def test_manager_can_create_companies(self, manager_client, manager_user):
        res = manager_client.post("/api/companies/", data={"name": "Test"}, format="json")
        assert res.status_code == 201

        company = Company.objects.get(id=res.data["id"])
        assert company.name == "Test"
        assert company.created_by == manager_user

    def test_sales_rep_can_create_companies(self, sales_rep_client, sales_rep_user):
        res = sales_rep_client.post("/api/companies/", data={"name": "Test"}, format="json")
        assert res.status_code == 201

        company = Company.objects.get(id=res.data["id"])
        assert company.name == "Test"
        assert company.created_by == sales_rep_user

    def test_employee_cannot_create_companies(self, employee_client, employee_user):
        res = employee_client.post("/api/companies/", data={"name": "Test"}, format="json")
        assert res.status_code == 403

    def test_create_company_without_required_fields_fails(self, admin_client):
        res = admin_client.post("/api/companies/")
        assert res.status_code == 400

    # /api/companies/{company-id}/
    # retrieve
    def test_admin_can_retrieve_company(self, admin_client):
        company = CompanyFactory()
        res = admin_client.get(f"/api/companies/{company.id}/")
        assert res.status_code == 200

    def test_manager_can_retrieve_company(self, manager_client):
        company = CompanyFactory()
        res = manager_client.get(f"/api/companies/{company.id}/")
        assert res.status_code == 200

    def test_sales_rep_can_retrieve_company(self, sales_rep_client):
        company = CompanyFactory()
        res = sales_rep_client.get(f"/api/companies/{company.id}/")
        assert res.status_code == 200

    def test_employee_cannot_retrieve_company(self, employee_client):
        company = CompanyFactory()
        res = employee_client.get(f"/api/companies/{company.id}/")
        assert res.status_code == 403

    def test_retrieve_response_fields(self, admin_client):
        company = CompanyFactory()
        res = admin_client.get(f"/api/companies/{company.id}/")

        # перевіряємо, що повертаються правильні поля
        company_data = res.data
        assert company_data["id"] == str(company.id)
        assert company_data["name"] == company.name
        assert company_data["description"] == company.description
        assert company_data["industry"] == company.industry
        assert company_data["website"] == company.website
        assert company_data["email"] == company.email
        assert company_data["instagram_url"] == company.instagram_url
        assert company_data["facebook_url"] == company.facebook_url
        assert parse_datetime(company_data["created_at"]) == company.created_at
        assert (list(str(contact_id) for contact_id in company_data["contacts"]) ==
                list(str(contact.id) for contact in company.contacts.all()))
        assert company_data["created_by"] == company.created_by.id
        assert (list(str(deal_id) for deal_id in company_data["deals"]) ==
                list(str(deal.id) for deal in company.deals.all()))

    # partial_update
    def test_admin_can_update_company(self, admin_client):
        company = CompanyFactory()
        new_company_data = {
            "name": "New Name",
            "description": "new description",
            "industry": "new industry",
            "website": "http://www.newsite.com",
            "email": "new_mail@test.com",
            "instagram_url": "http://www.newinstagram.com",
            "facebook_url": "http://www.newfacebook.com",
        }
        res = admin_client.patch(f"/api/companies/{company.id}/", data=new_company_data, format="json")
        assert res.status_code == 200

        company.refresh_from_db()
        assert company.name == new_company_data["name"]
        assert company.description == new_company_data["description"]
        assert company.industry == new_company_data["industry"]
        assert company.website == new_company_data["website"]
        assert company.email == new_company_data["email"]
        assert company.instagram_url == new_company_data["instagram_url"]
        assert company.facebook_url == new_company_data["facebook_url"]

    def test_manager_can_update_company(self, manager_client):
        company = CompanyFactory()
        new_company_data = {
            "name": "New Name",
            "description": "new description",
            "industry": "new industry",
            "website": "http://www.newsite.com",
            "email": "new_mail@test.com",
            "instagram_url": "http://www.newinstagram.com",
            "facebook_url": "http://www.newfacebook.com",
        }
        res = manager_client.patch(f"/api/companies/{company.id}/", data=new_company_data, format="json")
        assert res.status_code == 200

        company.refresh_from_db()
        assert company.name == new_company_data["name"]
        assert company.description == new_company_data["description"]
        assert company.industry == new_company_data["industry"]
        assert company.website == new_company_data["website"]
        assert company.email == new_company_data["email"]
        assert company.instagram_url == new_company_data["instagram_url"]
        assert company.facebook_url == new_company_data["facebook_url"]

    def test_sales_rep_can_update_company(self, sales_rep_client):
        company = CompanyFactory()
        new_company_data = {
            "name": "New Name",
            "description": "new description",
            "industry": "new industry",
            "website": "http://www.newsite.com",
            "email": "new_mail@test.com",
            "instagram_url": "http://www.newinstagram.com",
            "facebook_url": "http://www.newfacebook.com",
        }
        res = sales_rep_client.patch(f"/api/companies/{company.id}/", data=new_company_data, format="json")
        assert res.status_code == 200

        company.refresh_from_db()
        assert company.name == new_company_data["name"]
        assert company.description == new_company_data["description"]
        assert company.industry == new_company_data["industry"]
        assert company.website == new_company_data["website"]
        assert company.email == new_company_data["email"]
        assert company.instagram_url == new_company_data["instagram_url"]
        assert company.facebook_url == new_company_data["facebook_url"]

    def test_employee_cannot_update_company(self, employee_client):
        company = CompanyFactory()
        new_company_data = {
            "name": "New Name",
            "description": "new description",
            "industry": "new industry",
            "website": "http://www.newsite.com",
            "email": "new_mail@test.com",
            "instagram_url": "http://www.newinstagram.com",
            "facebook_url": "http://www.newfacebook.com",
        }
        res = employee_client.patch(f"/api/companies/{company.id}/", data=new_company_data, format="json")
        assert res.status_code == 403

    def test_readonly_fields_are_ignored_on_update(self, admin_client):
        company = CompanyFactory()
        contacts = ContactFactory.create_batch(3)
        deals = DealFactory.create_batch(3)
        new_data = {
            "id": "00000000-0000-0000-0000-000000000000",
            "contacts": [str(contact.id) for contact in contacts],
            "deals": [str(deal.id) for deal in deals],
            "created_by": "00000000-0000-0000-0000-000000000000",
            "created_at": "2026-01-01T10:00:00Z"
        }
        res = admin_client.patch(f"/api/companies/{company.id}/", data=new_data, format="json")
        assert res.status_code == 200

        company.refresh_from_db()
        assert company.id != new_data["id"]
        assert list(str(contact.id) for contact in company.contacts.all()) == []
        assert list(str(deal.id) for deal in company.deals.all()) == []
        assert str(company.created_by.id) != new_data["created_by"]
        assert company.created_at != parse_datetime(new_data["created_at"])

    # delete
    def test_admin_can_delete_company(self, admin_client):
        company = CompanyFactory()
        res = admin_client.delete(f"/api/companies/{company.id}/")
        assert res.status_code == 204
        assert not Company.objects.filter(id=company.id).exists()

    def test_manager_can_delete_company(self, manager_client):
        company = CompanyFactory()
        res = manager_client.delete(f"/api/companies/{company.id}/")
        assert res.status_code == 204
        assert not Company.objects.filter(id=company.id).exists()

    def test_sales_rep_can_delete_company(self, sales_rep_client):
        company = CompanyFactory()
        res = sales_rep_client.delete(f"/api/companies/{company.id}/")
        assert res.status_code == 204
        assert not Company.objects.filter(id=company.id).exists()

    def test_employee_cannot_delete_company(self, employee_client):
        company = CompanyFactory()
        res = employee_client.delete(f"/api/companies/{company.id}/")
        assert res.status_code == 403


@pytest.mark.django_db
class TestCompaniesAddContactEndpoint:
    # /api/companies/{company-id}/add-contact/
    def test_admin_can_add_contact(self, admin_client):
        company = CompanyFactory()
        contact = ContactFactory(company=None)
        res = admin_client.post(f"/api/companies/{company.id}/add-contact/",
                                data={"contact": str(contact.id)},
                                format="json")
        assert res.status_code == 200
        # перевірка, чи дійсно contact було додано до company
        contact.refresh_from_db()
        assert contact.company == company

    def test_add_contact_already_in_same_company_fails(self, admin_client):
        company = CompanyFactory()
        contact = ContactFactory(company=company)
        res = admin_client.post(f"/api/companies/{company.id}/add-contact/",
                                data={"contact": str(contact.id)},
                                format="json")
        assert res.status_code == 400

    def test_add_contact_already_in_other_company_fails(self, admin_client):
        company = CompanyFactory()
        contact = ContactFactory()
        res = admin_client.post(f"/api/companies/{company.id}/add-contact/",
                                data={"contact": str(contact.id)},
                                format="json")
        assert res.status_code == 400

    def test_manager_can_add_contact(self, manager_client):
        company = CompanyFactory()
        contact = ContactFactory(company=None)
        res = manager_client.post(f"/api/companies/{company.id}/add-contact/",
                                  data={"contact": str(contact.id)},
                                  format="json")
        assert res.status_code == 200
        # перевірка, чи дійсно contact було додано до company
        contact.refresh_from_db()
        assert contact.company == company

    def test_sales_rep_can_add_contact(self, sales_rep_client):
        company = CompanyFactory()
        contact = ContactFactory(company=None)
        res = sales_rep_client.post(f"/api/companies/{company.id}/add-contact/",
                                    data={"contact": str(contact.id)},
                                    format="json")
        assert res.status_code == 200
        # перевірка, чи дійсно contact було додано до company
        contact.refresh_from_db()
        assert contact.company == company

    def test_employee_cannot_add_contact(self, employee_client):
        company = CompanyFactory()
        contact = ContactFactory(company=None)
        res = employee_client.post(f"/api/companies/{company.id}/add-contact/",
                                   data={"contact": str(contact.id)},
                                   format="json")
        assert res.status_code == 403


@pytest.mark.django_db
class TestCompaniesRemoveContactEndpoint:
    # /api/companies/{company-id}/remove-contact/
    def test_admin_can_remove_user(self, admin_client):
        company = CompanyFactory()
        contact = ContactFactory(company=company)
        res = admin_client.post(
            f"/api/companies/{company.id}/remove-contact/",
            data={"contact": str(contact.id)},
            format="json"
        )
        assert res.status_code == 200
        company.refresh_from_db()
        assert contact not in company.contacts.all()

    def test_manager_can_remove_user(self, manager_client):
        company = CompanyFactory()
        contact = ContactFactory(company=company)
        res = manager_client.post(
            f"/api/companies/{company.id}/remove-contact/",
            data={"contact": str(contact.id)},
            format="json"
        )
        assert res.status_code == 200
        company.refresh_from_db()
        assert contact not in company.contacts.all()

    def test_sales_rep_can_remove_user(self, sales_rep_client):
        company = CompanyFactory()
        contact = ContactFactory(company=company)
        res = sales_rep_client.post(
            f"/api/companies/{company.id}/remove-contact/",
            data={"contact": str(contact.id)},
            format="json"
        )
        assert res.status_code == 200
        company.refresh_from_db()
        assert contact not in company.contacts.all()

    def test_employee_cannot_remove_user(self, employee_client):
        company = CompanyFactory()
        contact = ContactFactory(company=company)
        res = employee_client.post(
            f"/api/companies/{company.id}/remove-contact/",
            data={"contact": str(contact.id)},
            format="json"
        )
        assert res.status_code == 403

    def test_remove_contact_not_in_company_fails(self, admin_client):
        company = CompanyFactory()
        contact = ContactFactory()
        res = admin_client.post(
            f"/api/companies/{company.id}/remove-contact/",
            data={"contact": str(contact.id)},
            format="json"
        )
        assert res.status_code == 400


@pytest.mark.django_db
class TestContactsEndpoint:
    # /api/contacts/
    # GET
    def test_admin_can_list_contacts(self, admin_client):
        ContactFactory.create_batch(3)
        res = admin_client.get("/api/contacts/")
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_manager_can_list_contacts(self, manager_client):
        ContactFactory.create_batch(3)
        res = manager_client.get("/api/contacts/")
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_sales_rep_can_list_contacts(self, sales_rep_client):
        ContactFactory.create_batch(3)
        res = sales_rep_client.get("/api/contacts/")
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_employee_cannot_list_contacts(self, employee_client):
        ContactFactory.create_batch(3)
        res = employee_client.get("/api/contacts/")
        assert res.status_code == 403

    def test_unauthenticated_cannot_list_contacts(self, api_client):
        ContactFactory.create_batch(3)
        res = api_client.get("/api/contacts/")
        assert res.status_code == 401

    def test_list_response_fields(self, admin_client):
        contact = ContactFactory()
        res = admin_client.get("/api/contacts/")

        contact_data = res.data[0]
        assert contact_data["id"] == str(contact.id)
        assert contact_data["first_name"] == contact.first_name
        assert contact_data["last_name"] == contact.last_name
        assert contact_data["email"] == contact.email
        assert contact_data["phone"] == contact.phone
        assert contact_data["city"] == contact.city
        assert contact_data["instagram_url"] == contact.instagram_url
        assert contact_data["facebook_url"] == contact.facebook_url
        assert parse_datetime(contact_data["created_at"]) == contact.created_at
        assert contact_data["status"] == contact.status
        assert contact_data["lead_source"] == contact.lead_source
        assert contact_data["company"] == contact.company.id
        assert contact_data["created_by"] == contact.created_by.id
        assert (list(str(activity_id) for activity_id in contact_data["activities"]) ==
                list(str(activity.id) for activity in contact.activities.all()))
        assert (list(str(deal_id) for deal_id in contact_data["deals"]) ==
                list(str(deal.id) for deal in contact.deals.all()))

    # POST
    def test_admin_can_create_contact(self, admin_client, admin_user):
        contact_data = {
            "first_name": "test first name",
            "last_name": "test last name",
            "lead_source": LeadSource.INSTAGRAM
        }
        res = admin_client.post("/api/contacts/", data=contact_data, format="json")
        assert res.status_code == 201

        contact = Contact.objects.get(id=res.data["id"])
        assert contact.first_name == contact_data["first_name"]
        assert contact.last_name == contact_data["last_name"]
        assert contact.lead_source == contact_data["lead_source"]
        assert contact.created_by == admin_user

    def test_manager_can_create_contact(self, manager_client, manager_user):
        contact_data = {
            "first_name": "test first name",
            "last_name": "test last name",
            "lead_source": LeadSource.INSTAGRAM
        }
        res = manager_client.post("/api/contacts/", data=contact_data, format="json")
        assert res.status_code == 201

        contact = Contact.objects.get(id=res.data["id"])
        assert contact.first_name == contact_data["first_name"]
        assert contact.last_name == contact_data["last_name"]
        assert contact.lead_source == contact_data["lead_source"]
        assert contact.created_by == manager_user

    def test_sales_rep_can_create_contact(self, sales_rep_client, sales_rep_user):
        contact_data = {
            "first_name": "test first name",
            "last_name": "test last name",
            "lead_source": LeadSource.INSTAGRAM
        }
        res = sales_rep_client.post("/api/contacts/", data=contact_data, format="json")
        assert res.status_code == 201

        contact = Contact.objects.get(id=res.data["id"])
        assert contact.first_name == contact_data["first_name"]
        assert contact.last_name == contact_data["last_name"]
        assert contact.lead_source == contact_data["lead_source"]
        assert contact.created_by == sales_rep_user

    def test_employee_cannot_create_contacts(self, employee_client, employee_user):
        contact_data = {
            "first_name": "test first name",
            "last_name": "test last name",
            "lead_source": LeadSource.INSTAGRAM
        }
        res = employee_client.post("/api/contacts/", data=contact_data, format="json")
        assert res.status_code == 403

    def test_create_contact_without_required_fields_fails(self, admin_client):
        res = admin_client.post("/api/contacts/")
        assert res.status_code == 400
        assert "first_name" in res.data
        assert "last_name" in res.data
        assert "lead_source" in res.data

    # /api/contacts/{contact-id}/
    # retrieve
    def test_admin_can_retrieve_contact(self, admin_client):
        contact = ContactFactory()
        res = admin_client.get(f"/api/contacts/{contact.id}/")
        assert res.status_code == 200

    def test_manager_can_retrieve_contact(self, manager_client):
        contact = ContactFactory()
        res = manager_client.get(f"/api/contacts/{contact.id}/")
        assert res.status_code == 200

    def test_sales_rep_can_retrieve_contact(self, sales_rep_client):
        contact = ContactFactory()
        res = sales_rep_client.get(f"/api/contacts/{contact.id}/")
        assert res.status_code == 200

    def test_employee_cannot_retrieve_contact(self, employee_client):
        contact = ContactFactory()
        res = employee_client.get(f"/api/contacts/{contact.id}/")
        assert res.status_code == 403

    def test_retrieve_response_fields(self, admin_client):
        contact = ContactFactory()
        res = admin_client.get(f"/api/contacts/{contact.id}/")

        # перевіряємо, що повертаються правильні поля
        contact_data = res.data
        assert contact_data["id"] == str(contact.id)
        assert contact_data["first_name"] == contact.first_name
        assert contact_data["last_name"] == contact.last_name
        assert contact_data["email"] == contact.email
        assert contact_data["phone"] == contact.phone
        assert contact_data["city"] == contact.city
        assert contact_data["instagram_url"] == contact.instagram_url
        assert contact_data["facebook_url"] == contact.facebook_url
        assert parse_datetime(contact_data["created_at"]) == contact.created_at
        assert contact_data["status"] == contact.status
        assert contact_data["lead_source"] == contact.lead_source
        assert contact_data["company"] == contact.company.id
        assert contact_data["created_by"] == contact.created_by.id
        assert (list(str(activity_id) for activity_id in contact_data["activities"]) ==
                list(str(activity.id) for activity in contact.activities.all()))
        assert (list(str(deal_id) for deal_id in contact_data["deals"]) ==
                list(str(deal.id) for deal in contact.deals.all()))

    # partial_update
    def test_admin_can_update_contact(self, admin_client):
        contact = ContactFactory()
        company = CompanyFactory()
        new_contact_data = {
            "first_name": "New first name",
            "last_name": "New last name",
            "email": "new_mail@test.com",
            "phone": "0123456789",
            "city": "New city",
            "instagram_url": "http://www.newinstagram.com",
            "facebook_url": "http://www.newfacebook.com",
            "status": ContactStatus.ACTIVE,
            "lead_source": LeadSource.WEBSITE,
            "company": str(company.id),
        }
        res = admin_client.patch(f"/api/contacts/{contact.id}/", data=new_contact_data, format="json")
        assert res.status_code == 200

        contact.refresh_from_db()
        assert contact.first_name == new_contact_data["first_name"]
        assert contact.last_name == new_contact_data["last_name"]
        assert contact.email == new_contact_data["email"]
        assert contact.phone == new_contact_data["phone"]
        assert contact.city == new_contact_data["city"]
        assert contact.instagram_url == new_contact_data["instagram_url"]
        assert contact.facebook_url == new_contact_data["facebook_url"]
        assert contact.status == new_contact_data["status"]
        assert contact.lead_source == new_contact_data["lead_source"]
        assert str(contact.company.id) == new_contact_data["company"]

    def test_manager_can_update_contact(self, manager_client):
        contact = ContactFactory()
        company = CompanyFactory()
        new_contact_data = {
            "first_name": "New first name",
            "last_name": "New last name",
            "email": "new_mail@test.com",
            "phone": "0123456789",
            "city": "New city",
            "instagram_url": "http://www.newinstagram.com",
            "facebook_url": "http://www.newfacebook.com",
            "status": ContactStatus.ACTIVE,
            "lead_source": LeadSource.WEBSITE,
            "company": str(company.id),
        }
        res = manager_client.patch(f"/api/contacts/{contact.id}/", data=new_contact_data, format="json")
        assert res.status_code == 200

        contact.refresh_from_db()
        assert contact.first_name == new_contact_data["first_name"]
        assert contact.last_name == new_contact_data["last_name"]
        assert contact.email == new_contact_data["email"]
        assert contact.phone == new_contact_data["phone"]
        assert contact.city == new_contact_data["city"]
        assert contact.instagram_url == new_contact_data["instagram_url"]
        assert contact.facebook_url == new_contact_data["facebook_url"]
        assert contact.status == new_contact_data["status"]
        assert contact.lead_source == new_contact_data["lead_source"]
        assert str(contact.company.id) == new_contact_data["company"]

    def test_sales_rep_can_update_contact(self, sales_rep_client):
        contact = ContactFactory()
        company = CompanyFactory()
        new_contact_data = {
            "first_name": "New first name",
            "last_name": "New last name",
            "email": "new_mail@test.com",
            "phone": "0123456789",
            "city": "New city",
            "instagram_url": "http://www.newinstagram.com",
            "facebook_url": "http://www.newfacebook.com",
            "status": ContactStatus.ACTIVE,
            "lead_source": LeadSource.WEBSITE,
            "company": str(company.id),
        }
        res = sales_rep_client.patch(f"/api/contacts/{contact.id}/", data=new_contact_data, format="json")
        assert res.status_code == 200

        contact.refresh_from_db()
        assert contact.first_name == new_contact_data["first_name"]
        assert contact.last_name == new_contact_data["last_name"]
        assert contact.email == new_contact_data["email"]
        assert contact.phone == new_contact_data["phone"]
        assert contact.city == new_contact_data["city"]
        assert contact.instagram_url == new_contact_data["instagram_url"]
        assert contact.facebook_url == new_contact_data["facebook_url"]
        assert contact.status == new_contact_data["status"]
        assert contact.lead_source == new_contact_data["lead_source"]
        assert str(contact.company.id) == new_contact_data["company"]

    def test_employee_cannot_update_contact(self, employee_client):
        contact = ContactFactory()
        res = employee_client.patch(f"/api/contacts/{contact.id}/", data={}, format="json")
        assert res.status_code == 403

    def test_readonly_fields_are_ignored_on_update(self, admin_client):
        contact = ContactFactory()
        deals = DealFactory.create_batch(3)
        activities = ActivityFactory.create_batch(3)
        new_data = {
            "id": "00000000-0000-0000-0000-000000000000",
            "deals": [str(deal.id) for deal in deals],
            "activities": [str(activity.id) for activity in activities],
            "created_by": "00000000-0000-0000-0000-000000000000",
            "created_at": "2026-01-01T10:00:00Z"
        }
        res = admin_client.patch(f"/api/contacts/{contact.id}/", data=new_data, format="json")
        assert res.status_code == 200

        contact.refresh_from_db()
        assert contact.id != new_data["id"]
        assert list(str(deal.id) for deal in contact.deals.all()) == []
        assert list(str(activity.id) for activity in contact.activities.all()) == []
        assert str(contact.created_by.id) != new_data["created_by"]
        assert contact.created_at != parse_datetime(new_data["created_at"])

    # delete
    def test_admin_can_delete_contact(self, admin_client):
        contact = ContactFactory()
        res = admin_client.delete(f"/api/contacts/{contact.id}/")
        assert res.status_code == 204
        assert not Contact.objects.filter(id=contact.id).exists()

    def test_manager_can_delete_contact(self, manager_client):
        contact = ContactFactory()
        res = manager_client.delete(f"/api/contacts/{contact.id}/")
        assert res.status_code == 204
        assert not Contact.objects.filter(id=contact.id).exists()

    def test_sales_rep_can_delete_contact(self, sales_rep_client):
        contact = ContactFactory()
        res = sales_rep_client.delete(f"/api/contacts/{contact.id}/")
        assert res.status_code == 204
        assert not Contact.objects.filter(id=contact.id).exists()

    def test_employee_cannot_delete_contact(self, employee_client):
        contact = ContactFactory()
        res = employee_client.delete(f"/api/contacts/{contact.id}/")
        assert res.status_code == 403
