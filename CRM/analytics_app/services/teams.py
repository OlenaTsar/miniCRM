from django.db.models import Avg, F, ExpressionWrapper, DurationField
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from auth_app.models import UserRole, User, Team
from crm_app.models import (
    Deal,
    Activity,
    PipelineStage,
)


class TeamAnalyticsService:
    def __init__(self, request):
        self.request = request
        self.teams = Team.objects.all()

    def get_total_deals(self, team):
        return Deal.objects.filter(assigned_to__team=team).count()

    def get_total_won_deals(self, team):
        return Deal.objects.filter(stage=PipelineStage.CLOSED_WON, assigned_to__team=team).count()

    def get_amount_average_won_deals(self, team):
        amount_average = Deal.objects.filter(
            stage=PipelineStage.CLOSED_WON,
            assigned_to__team=team,
        ).aggregate(
            amount_average=Avg("amount")
        )['amount_average']
        return round(amount_average, 2) if amount_average is not None else None

    def get_completed_activities(self, team):
        return Activity.objects.filter(
            assigned_to__team=team,
            completed_at__isnull=False,
        ).count()

    def get_overdue_activities(self, team):
        return Activity.objects.filter(
            assigned_to__team=team,
            completed_at__isnull=True,
            due_date__lt=timezone.now(),
        ).count()

    def get_avg_activities_per_won_deal(self, team):
        # Скільки в середньому потрібно activity для успішної угоди
        activity_count = Activity.objects.filter(
            deal__stage=PipelineStage.CLOSED_WON,
            assigned_to__team=team,
        ).count()
        deal_count = Deal.objects.filter(
            stage=PipelineStage.CLOSED_WON,
            assigned_to__team=team,
        ).count()

        return round(activity_count / deal_count, 2) if deal_count else None

    def get_average_deal_duration(self, team):
        # середній час закриття угоди
        duration = (
            Deal.objects.filter(
                assigned_to__team=team,
            ).annotate(
                duration=ExpressionWrapper(
                    F("closed_at") - F("created_at"),
                    output_field=DurationField(),
                )
            )
            .aggregate(average_duration=Avg("duration"))
        )['average_duration']
        return round(duration.total_seconds() / 86400, 2) if duration is not None else None

    def get_data(self):
        result = []

        for team in self.teams:
            managers = []
            sales = []
            for user in team.users.all():
                if user.role == 'manager':
                    managers.append(user.email)
                elif user.role == 'sales_rep':
                    sales.append(user.email)

            total_deals = self.get_total_deals(team)
            total_won_deals = self.get_total_won_deals(team)

            if total_deals:
                conversion = round(total_won_deals / total_deals * 100, 2)
            else:
                conversion = None

            result.append({
                "team_name": team.name,
                "managers": managers,
                "sales_reps": sales,
                "total_deals": total_deals,
                "total_won_deals": total_won_deals,
                "conversion": conversion,
                "amount_average_won_deals": self.get_amount_average_won_deals(team),
                "completed_activities": self.get_completed_activities(team),
                "overdue_activities": self.get_overdue_activities(team),
                "avg_activities_per_won_deal": self.get_avg_activities_per_won_deal(team),
                "average_deal_duration": self.get_average_deal_duration(team),
            })

        return result
