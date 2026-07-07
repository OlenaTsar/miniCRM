from django.db.models import Count, Q, Sum, Avg, F, ExpressionWrapper, DurationField

from auth_app.models import UserRole, User, Team
from crm_app.models import (
    Deal,
    PipelineStage,
    DealStatus,
    Pipeline,
)
from crm_app.filters import DealFilter


class AnalyticsService:
    def __init__(self, request):
        self.request = request
        self.user = request.user
        self.visible_users = self._get_visible_users()
        self.deals = self._get_deals()

    def _get_visible_users(self):
        if self.user.role == UserRole.ADMIN:
            return User.objects.all()
        elif self.user.role == UserRole.MANAGER:
            return User.objects.filter(team=self.user.team)
        elif self.user.role == UserRole.SALES_REP:
            return [self.user]
        else:
            return User.objects.none()

    def _get_deals(self):
        queryset = Deal.objects.filter(assigned_to__in=self.visible_users)

        return DealFilter(
            self.request.GET,
            queryset=queryset,
        ).qs


class DealAnalyticsService(AnalyticsService):
    def __init__(self, request, deals=None):
        if deals is not None:
            self.deals = deals
        else:
            super().__init__(request)

    def get_by_stage(self):
        """
        статистика по угодам для кожного stage

        повертає список зі статистикою по кожному stage
        {
            "stage":
            "count":
            "on_hold":
            "total_amount":
            "conversion":
        }
        """
        stage_stats = (
            self.deals
            .values("stage")
            .annotate(
                count=Count("id"),
                on_hold=Count(
                    "id",
                    filter=Q(status=DealStatus.ON_HOLD),
                ),
                total_amount=Sum("amount"),
            )
        )

        # словник для швидкого доступу по stage
        stats = {
            item["stage"]: item
            for item in stage_stats
        }

        result = []

        previous_count = None

        stage_order = [
            PipelineStage.NEW_LEAD,
            PipelineStage.QUALIFICATION,
            PipelineStage.PROPOSAL_SENT,
            PipelineStage.NEGOTIATION,
            PipelineStage.CLOSED_WON,
            PipelineStage.CLOSED_LOST,
        ]

        for stage in stage_order:
            item = stats.get(stage, {})

            count = item.get("count", 0)

            if stage in (
                    PipelineStage.NEW_LEAD,
                    PipelineStage.CLOSED_LOST,
            ):
                conversion = None

            elif previous_count:
                conversion = round(count / previous_count * 100, 2)

            else:
                conversion = None

            result.append({
                "stage": stage,
                "count": count,
                "on_hold": item.get("on_hold", 0),
                "total_amount": item.get("total_amount") or 0,
                "conversion": conversion,
            })

            if stage != PipelineStage.CLOSED_LOST:
                previous_count = count

        return result

    def get_won(self):
        # загальна кількість виграних deals (PipelineStage=CLOSED_WON)
        return self.deals.filter(stage=PipelineStage.CLOSED_WON).count()

    def get_lost(self):
        # загальна кількість програних deals (PipelineStage=CLOSED_LOST)
        return self.deals.filter(stage=PipelineStage.CLOSED_LOST).count()

    def get_avg_amount(self):
        # avg won deals amount
        amount_average = self.deals.filter(stage=PipelineStage.CLOSED_WON).aggregate(
            amount_average=Avg("amount")
        )['amount_average']
        return round(amount_average, 2) if amount_average is not None else None

    def get_avg_deal_duration(self):
        # середній час закриття угоди
        duration = (
            self.deals.annotate(
                duration=ExpressionWrapper(
                    F("closed_at") - F("created_at"),
                    output_field=DurationField(),
                )
            )
            .aggregate(average_duration=Avg("duration"))
        )['average_duration']
        return round(duration.total_seconds() / 86400, 2) if duration is not None else None

    def get_data(self):
        result = dict()

        result["total"] = self.deals.count()
        result["by_stage"] = self.get_by_stage()
        result["won"] = self.get_won()
        result["lost"] = self.get_lost()
        if result["total"]:
            result["total_conversion"] = round(result["won"] / result["total"] * 100, 2)
        else:
            result["total_conversion"] = None
        result["amount_average_won_deals"] = self.get_avg_amount()
        result["average_deal_duration"] = self.get_avg_deal_duration()  # days

        return result


class DealByPipelineAnalyticsService(AnalyticsService):
    def __init__(self, request):
        super().__init__(request)
        self.pipelines = self._get_pipelines()

    def _get_pipelines(self):
        return Pipeline.objects.filter(assigned_to__in=self.visible_users)

    def get_data(self):
        result = []

        for pipeline in self.pipelines:
            pipeline_deals = self.deals.filter(pipeline=pipeline)
            result.append({
                "pipeline_name": pipeline.name,
                "product": pipeline.product.name,
                "assigned_to": pipeline.assigned_to.email,
                "analytics": DealAnalyticsService(request=self.request, deals=pipeline_deals).get_data(),
            })

        return result


class DealByTeamsAnalyticsService:
    def __init__(self, request):
        self.request = request
        self.deals = self._get_deals()
        self.teams = Team.objects.all()

    def _get_deals(self):
        # для фільтрації угод, якщо при запиті були використані фільтри

        return DealFilter(
            self.request.GET,
            queryset=Deal.objects.all(),
        ).qs

    def get_data(self):
        result = []

        for team in self.teams:
            team_deals = self.deals.filter(assigned_to__team=team)

            # в команди може бути один менеджер, не бути жодного або бути декілька
            # тому враховуються всі випадки
            managers = []
            for manager in team.users.filter(role='manager'):
                managers.append(manager.email)
            result.append({
                "team_name": team.name,
                "managers": managers,
                "analytics": DealAnalyticsService(request=self.request, deals=team_deals).get_data(),
            })

        return result
