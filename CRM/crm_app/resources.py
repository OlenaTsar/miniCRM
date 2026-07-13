from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget

from auth_app.models import User
from .models import Contact, Company, Deal, Activity, Pipeline, Product


class ContactResource(resources.ModelResource):
    # повертає email замість id
    created_by = fields.Field(
        column_name="created_by",
        attribute="created_by",
        widget=ForeignKeyWidget(User, field="email")
    )
    # повертає company name замість id
    company = fields.Field(
        column_name="company",
        attribute="company",
        widget=ForeignKeyWidget(Company, field="name")
    )

    class Meta:
        model = Contact
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'city',
            'company',
            'instagram_url',
            'facebook_url',
            'status',
            'lead_source',
            'created_by',
        ]
        import_id_fields = ["email"]  # унікальний ідентифікатор

    def before_import_row(self, row, **kwargs):
        row["created_by"] = str(self.user.id)


class ContactReportResource(resources.ModelResource):
    # повертає email замість id
    created_by = fields.Field(
        column_name="created_by",
        attribute="created_by",
        widget=ForeignKeyWidget(User, field="email")
    )
    # повертає company name замість id
    company = fields.Field(
        column_name="company",
        attribute="company",
        widget=ForeignKeyWidget(Company, field="name")
    )
    # повертає всі deals name для кожного контакту
    deals_name = fields.Field(
        column_name="deals_name",
        attribute="deals",
        widget=ManyToManyWidget(Deal, field="name", separator='\n')
    )
    # повертає кількість угод для кожного контакту
    deals_count = fields.Field(column_name="deals_count")

    def dehydrate_deals_count(self, contact):
        return contact.deals.count()
    # повертає кількість активностей для кожного контакту
    activities_count = fields.Field(column_name="activities_count")

    def dehydrate_activities_count(self, contact):
        return contact.activities.count()

    class Meta:
        model = Contact
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'city',
            'company',
            'instagram_url',
            'facebook_url',
            'status',
            'deals_name',
            'deals_count',
            'activities_count',
            'lead_source',
            'created_by',
        ]


class DealReportResource(resources.ModelResource):
    # повертає email замість id
    assigned_to = fields.Field(
        column_name="assigned_to",
        attribute="assigned_to",
        widget=ForeignKeyWidget(User, field="email")
    )
    # повертає pipeline name замість id
    pipeline = fields.Field(
        column_name="pipeline",
        attribute="pipeline",
        widget=ForeignKeyWidget(Pipeline, field="name")
    )
    # повертає product name замість id
    product = fields.Field(
        column_name="product",
        attribute="product",
        widget=ForeignKeyWidget(Product, field="name")
    )
    # повертає всі Contact name для deals
    contacts = fields.Field(column_name="contacts")

    def dehydrate_contacts(self, deal):
        return "\n".join([
            f"{c.first_name} {c.last_name}"
            for c in deal.contacts.all()
        ])

    class Meta:
        model = Deal
        fields = [
            'name',
            'description',
            'status',
            'stage',
            'amount',
            'currency',
            'expected_close_date',
            'created_at',
            'closed_at',
            'pipeline',
            'product',
            'contacts',
            'assigned_to',
        ]


class ActivityReportResource(resources.ModelResource):
    # повертає email замість id
    assigned_to = fields.Field(
        column_name="assigned_to",
        attribute="assigned_to",
        widget=ForeignKeyWidget(User, field="email")
    )
    # повертає deal name замість id
    deal = fields.Field(
        column_name="deal",
        attribute="deal",
        widget=ForeignKeyWidget(Deal, field="name")
    )
    # повертає contact name замість id
    contact = fields.Field(column_name="contact")

    def dehydrate_contact(self, activity):
        return f"{activity.contact.first_name} {activity.contact.last_name}"

    class Meta:
        model = Activity
        fields = [
            'title',
            'description',
            'activity_type',
            'contact',
            'deal',
            'outcome',
            'created_at',
            'due_date',
            'completed_at',
            'assigned_to',
        ]
