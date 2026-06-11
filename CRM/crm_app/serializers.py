from rest_framework import serializers

from .models import Company, Contact, Product, Deal, Pipeline, PipelineStage, DealStageHistory
from auth_app.models import UserRole


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


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'teams',
        ]
        read_only_fields = [
            'id',
            'teams'
        ]

    # щоб SalesRep не мав доступу до перегляду teams
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request and request.user.role == UserRole.SALES_REP:
            data.pop("teams", None)
        return data


class PipelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pipeline
        fields = [
            'id',
            'name',
            'created_at',
            'assigned_to',
            'product',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'product',
        ]

    def validate(self, attrs):
        # забороняє SALES_REP змінювати assigned_to

        user = self.context["request"].user

        if (
                user.role == UserRole.SALES_REP
                and "assigned_to" in attrs
        ):
            raise serializers.ValidationError(
                {"assigned_to": "You cannot change assignee."}
            )

        return attrs


class DealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deal
        fields = [
            'id',
            'name',
            'description',
            'status',
            'amount',
            'currency',
            'expected_close_date',
            'created_at',
            'stage',
            'is_final',
            'pipeline',
            'product',
            'contacts',
            'company',
            'assigned_to',
        ]
        read_only_fields = [
            'id',
            'created_at',
            # 'product',
            'stage',
            'status',
            'is_final',
        ]

    def validate(self, attrs):
        # забороняє SALES_REP змінювати assigned_to

        user = self.context["request"].user

        if (
                user.role == UserRole.SALES_REP
                and "assigned_to" in attrs
        ):
            raise serializers.ValidationError(
                {"assigned_to": "You cannot change assignee."}
            )

        return attrs


class ChangeStageSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=PipelineStage.choices)


class DealStageHistorySerializer(serializers.ModelSerializer):
    changed_by = serializers.StringRelatedField()  # для відображення __str__ юзера (email)

    class Meta:
        model = DealStageHistory
        fields = [
            "id",
            "old_stage",
            "new_stage",
            "changed_by",
            "changed_at",
        ]
        read_only_fields = fields
