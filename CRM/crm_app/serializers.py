from rest_framework import serializers

from .models import Company, Contact


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            'id',
            'name',
            'description',
            'industry',
            'website',
            'email',
            'instagram_url',
            'facebook_url',
            'created_at',
            'contacts',
            'assigned_to',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'contacts',
            'assigned_to',
        ]


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'phone',
            'city',
            'instagram_url',
            'facebook_url',
            'created_at',
            'status',
            'lead_source',
            'company',
            'assigned_to',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'assigned_to',
        ]
