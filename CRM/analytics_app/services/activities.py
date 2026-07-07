from django.db.models import Count, Q
from django.utils import timezone

from auth_app.models import UserRole, User, Team
from crm_app.models import (
    Activity,
    ActivityType,
    PipelineStage,
    Pipeline,
)
from crm_app.filters import ActivityFilter


class AnalyticsService:
    def __init__(self, request):
        self.request = request
        self.user = request.user
        self.visible_users = self._get_visible_users()
        self.activities = self._get_activities()

    def _get_visible_users(self):
        if self.user.role == UserRole.ADMIN:
            return User.objects.all()
        elif self.user.role == UserRole.MANAGER:
            return User.objects.filter(team=self.user.team)
        elif self.user.role == UserRole.SALES_REP:
            return [self.user]
        else:
            return User.objects.none()

    def _get_activities(self):
        queryset = Activity.objects.filter(assigned_to__in=self.visible_users)

        return ActivityFilter(
            self.request.GET,
            queryset=queryset,
        ).qs


class ActivityAnalyticsService(AnalyticsService):
    def __init__(self, request, activities=None):
        if activities is not None:
            self.activities = activities
        else:
            super().__init__(request)

    def get_completed(self):
        # кількість завершених (мають completed_at)
        return self.activities.filter(completed_at__isnull=False).count()

    def get_overdue(self):
        # прострочені активності (due_date яких вийшов і не мають completed_at)
        return self.activities.filter(completed_at__isnull=True, due_date__lt=timezone.now()).count()

    def get_total_by_type(self):
        # кількість активностей по кожному з типів ActivityType
        result = self.activities.values("activity_type").annotate(
            count=Count("id"),
            completed=Count("id", filter=Q(completed_at__isnull=False)),
            overdue=Count("id", filter=Q(completed_at__isnull=True, due_date__lt=timezone.now())),
        )

        return result

    def activities_per_won_deal(self):
        # Скільки в середньому потрібно activity для успішної угоди
        activity_count = self.activities.filter(deal__stage=PipelineStage.CLOSED_WON).count()
        deal_count = self.activities.filter(deal__stage=PipelineStage.CLOSED_WON).values("deal").distinct().count()

        return round(activity_count / deal_count, 2) if deal_count else None

    def get_data(self):
        result = dict()

        result["total"] = self.activities.count()
        result["completed"] = self.get_completed()
        result["overdue"] = self.get_overdue()
        result["total_by_type"] = self.get_total_by_type()
        result["avg_activities_per_won_deal"] = self.activities_per_won_deal()

        return result


class ActivityByPipelineAnalyticsService(AnalyticsService):
    def __init__(self, request):
        super().__init__(request)
        self.pipelines = self._get_pipelines()

    def _get_pipelines(self):
        return Pipeline.objects.filter(assigned_to__in=self.visible_users)

    def get_data(self):
        result = []

        for pipeline in self.pipelines:
            pipeline_activities = self.activities.filter(deal__pipeline=pipeline)
            result.append({
                "pipeline_name": pipeline.name,
                "product": pipeline.product.name,
                "assigned_to": pipeline.assigned_to.email,
                "analytics": ActivityAnalyticsService(request=self.request, activities=pipeline_activities).get_data(),
            })

        return result


class ActivityByTeamsAnalyticsService:
    def __init__(self, request):
        self.request = request
        self.activities = self._get_activities()
        self.teams = Team.objects.all()

    def _get_activities(self):
        # для фільтрації activities, якщо при запиті були використані фільтри

        return ActivityFilter(
            self.request.GET,
            queryset=Activity.objects.all(),
        ).qs

    def get_data(self):
        result = []

        for team in self.teams:
            team_activities = self.activities.filter(assigned_to__team=team)

            # в команди може бути один менеджер, не бути жодного або бути декілька
            # тому враховуються всі випадки
            managers = []
            for manager in team.users.filter(role='manager'):
                managers.append(manager.email)
            result.append({
                "team_name": team.name,
                "managers": managers,
                "analytics": ActivityAnalyticsService(request=self.request, activities=team_activities).get_data(),
            })

        return result
