from django.utils import timezone
from datetime import timedelta

from rest_framework import serializers

from .models import (
    Company,
    Contact,
    Product,
    Deal,
    Pipeline,
    PipelineStage,
    DealStageHistory,
    Activity,
    ActivityLog,
    Notification,
    ActivityScript,
)
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
            'created_by',
            'deals',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'contacts',
            'created_by',
            'deals',
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
            'created_by',
            'activities',
            'deals',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'created_by',
            'activities',
            'deals',
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
            'deals',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'deals',
        ]

    def get_fields(self):
        # щоб не можливо було змінити product після створення
        fields = super().get_fields()
        # якщо це оновлення (instance вже є) — product стає read_only
        if self.instance is not None:
            fields["product"].read_only = True
        return fields

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
            'closed_at',
            'pipeline',
            'product',
            'contact',
            'company',
            'assigned_to',
            'activities',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'product',
            'stage',
            'status',
            'closed_at',
            'activities',
        ]

    def get_fields(self):
        # щоб не можливо було змінити поля після створення
        fields = super().get_fields()
        if self.instance is not None:
            fields["contact"].read_only = True
        return fields

    def validate(self, attrs):
        # забороняє SALES_REP змінювати assigned_to

        user = self.context["request"].user

        if user.role == UserRole.SALES_REP and "assigned_to" in attrs:
            raise serializers.ValidationError(
                {"assigned_to": "You cannot change assignee."}
            )

        # якщо змінюється assigned_to
        # перевірка, чи має новий користувач відповідну pipline, щоб перемістити туди угоду
        if "assigned_to" in attrs and not attrs["assigned_to"].pipelines.filter(product=self.instance.product).exists():
            raise serializers.ValidationError(
                {"assigned_to": f"User {attrs["assigned_to"].email} do not have a "
                                f"Pipeline with Product {self.instance.product.name}."}
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


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = [
            'id',
            'title',
            'description',
            'activity_type',
            'outcome',
            'created_at',
            'due_date',
            'completed_at',
            'assigned_to',
            'deal',
            'contact',
            'script',
            'notification',
        ]
        read_only_fields = [
            'id',
            'contact',
            'created_at',
            'completed_at',
            'notification',
        ]

    def get_fields(self):
        # щоб не можливо було змінити поля після створення
        fields = super().get_fields()
        if self.instance is not None:
            fields["deal"].read_only = True
            fields["assigned_to"].read_only = True
            fields["activity_type"].read_only = True
        return fields

    def validate(self, attrs):
        now = timezone.now()

        # забороняє змінювати будь-які поля, окрім outcome, для завершеної Activity
        if self.instance and self.instance.completed_at:
            forbidden_fields = set(attrs.keys()) - {"outcome"}
            if forbidden_fields:
                raise serializers.ValidationError(
                    "You cannot change any fields except outcome in a completed activity."
                )

        # забороняє SALES_REP передавати при створенні assigned_to

        user = self.context["request"].user

        if user.role == UserRole.SALES_REP and "assigned_to" in attrs:
            raise serializers.ValidationError(
                {"assigned_to": "You cannot change assignee."}
            )

        # перевірка чи deal належить користувачеві, який створює активність, або переданому assigned_to
        if "assigned_to" in attrs and attrs["deal"].assigned_to != attrs["assigned_to"]:
            raise serializers.ValidationError(
                {"deal": f"Deal must be assigned to user {attrs["assigned_to"].email}."}
            )
        if "assigned_to" not in attrs and attrs["deal"].assigned_to != user:
            raise serializers.ValidationError(
                {"deal": f"Deal must be assigned to you."}
            )

        # перевіряємо чи коректний due_date
        if "due_date" in attrs and attrs["due_date"] < now + timedelta(minutes=5):
            raise serializers.ValidationError(
                {"due_date": "Activity due date must be more than 5 minutes from the current time."}
            )

        return attrs

    def create(self, validated_data):
        # щоб передати _changed_by в signal
        activity = Activity(**validated_data)
        activity._changed_by = self.context["request"].user
        activity.save()
        return activity


class ActivityLogSerializer(serializers.ModelSerializer):
    performed_by = serializers.StringRelatedField()  # для відображення __str__ юзера (email)

    class Meta:
        model = ActivityLog
        fields = [
            'id',
            'action',
            'old_data',
            'new_data',
            'timestamp',
            'performed_by',
        ]
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id',
            'notify_at',
            'sent_at',
            'read_at',
            'recipient',
            'activity',
        ]
        read_only_fields = fields


class ActivityScriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityScript
        fields = [
            'id',
            'title',
            'text',
            'attachment',
            'activity_type',
            'stage',
            'product',
            'created_by',
            'activities',
        ]
        read_only_fields = [
            'id',
            'created_by',
            'activities',
        ]
