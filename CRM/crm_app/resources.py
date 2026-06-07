from import_export import resources
from .models import Contact


class ContactResource(resources.ModelResource):
    class Meta:
        model = Contact
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'city',
            'instagram_url',
            'facebook_url',
            'status',
            'lead_source',
            'assigned_to',
        ]
        import_id_fields = ["email"]  # унікальний ідентифікатор

    def before_import_row(self, row, **kwargs):
        row["assigned_to"] = str(self.user.id)
