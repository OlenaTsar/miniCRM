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
            'user',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'contacts',
            'user',
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
            'instagram_url',
            'facebook_url',
            'created_at',
            'status',
            'lead_source',
            'company',
            'user',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'user',
        ]
