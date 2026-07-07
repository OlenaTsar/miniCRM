from rest_framework import serializers

from crm_app.models import PipelineStage, ActivityType, ContactStatus, LeadSource


class DealStageAnalyticsSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=PipelineStage.choices)
    count = serializers.IntegerField()
    on_hold = serializers.IntegerField()
    total_amount = serializers.FloatField()
    conversion = serializers.FloatField(allow_null=True)


class DealAnalyticsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    by_stage = DealStageAnalyticsSerializer(many=True)
    won = serializers.IntegerField()
    lost = serializers.IntegerField()
    total_conversion = serializers.FloatField()
    amount_average_won_deals = serializers.FloatField()
    average_deal_duration = serializers.FloatField()


class DealByPipelineAnalyticsSerializer(serializers.Serializer):
    pipeline_name = serializers.CharField()
    product = serializers.CharField()
    assigned_to = serializers.EmailField()
    analytics = DealAnalyticsSerializer()


class DealByTeamsAnalyticsSerializer(serializers.Serializer):
    team_name = serializers.CharField()
    managers = serializers.ListField(child=serializers.EmailField())
    analytics = DealAnalyticsSerializer()


class ActivityTypeAnalyticsSerializer(serializers.Serializer):
    activity_type = serializers.ChoiceField(choices=ActivityType.choices)
    count = serializers.IntegerField()
    completed = serializers.IntegerField()
    overdue = serializers.IntegerField()


class ActivityAnalyticsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    completed = serializers.IntegerField()
    overdue = serializers.IntegerField()
    total_by_type = ActivityTypeAnalyticsSerializer(many=True)
    avg_activities_per_won_deal = serializers.FloatField(allow_null=True)


class ActivityByPipelineAnalyticsSerializer(serializers.Serializer):
    pipeline_name = serializers.CharField()
    product = serializers.CharField()
    assigned_to = serializers.EmailField()
    analytics = ActivityAnalyticsSerializer()


class ActivityByTeamsAnalyticsSerializer(serializers.Serializer):
    team_name = serializers.CharField()
    managers = serializers.ListField(child=serializers.EmailField())
    analytics = ActivityAnalyticsSerializer()


class ContactStatusAnalyticsSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ContactStatus.choices)
    count = serializers.IntegerField()


class ContactLeadSourceAnalyticsSerializer(serializers.Serializer):
    lead_source = serializers.ChoiceField(choices=LeadSource.choices)
    count = serializers.IntegerField()
    won_deals = serializers.IntegerField()


class ContactAnalyticsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    new_from_last_week = serializers.IntegerField()
    new_from_last_month = serializers.IntegerField()
    total_by_contact_status = ContactStatusAnalyticsSerializer(many=True)
    total_by_lead_source = ContactLeadSourceAnalyticsSerializer(many=True)


class ContactByPipelineAnalyticsSerializer(serializers.Serializer):
    pipeline_name = serializers.CharField()
    product = serializers.CharField()
    assigned_to = serializers.EmailField()
    analytics = ContactAnalyticsSerializer()


class ContactByTeamsAnalyticsSerializer(serializers.Serializer):
    team_name = serializers.CharField()
    managers = serializers.ListField(child=serializers.EmailField())
    analytics = ContactAnalyticsSerializer()


class TeamAnalyticsSerializer(serializers.Serializer):
    team_name = serializers.CharField()
    managers = serializers.ListField(child=serializers.EmailField())
    sales_reps = serializers.ListField(child=serializers.EmailField())
    total_deals = serializers.IntegerField()
    total_won_deals = serializers.IntegerField()
    conversion = serializers.FloatField()
    amount_average_won_deals = serializers.FloatField()
    completed_activities = serializers.IntegerField()
    overdue_activities = serializers.IntegerField()
    avg_activities_per_won_deal = serializers.FloatField()
    average_deal_duration = serializers.FloatField()


class DashboardAnalyticsSerializer(serializers.Serializer):
    deals = DealAnalyticsSerializer()
    activities = ActivityAnalyticsSerializer()
    contacts = ContactAnalyticsSerializer()
