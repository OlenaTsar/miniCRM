from django.db.models import Count, Q
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from auth_app.models import UserRole, User, Team
from crm_app.models import (
    Contact,
    ContactStatus,
    LeadSource,
    PipelineStage,
    Pipeline,
)
from crm_app.filters import ContactFilter


class AnalyticsService:
    def __init__(self, request):
        self.request = request
        self.user = request.user
        self.visible_users = self._get_visible_users()
        self.contacts = self._get_contacts()

    def _get_visible_users(self):
        if self.user.role == UserRole.ADMIN:
            return User.objects.all()
        elif self.user.role == UserRole.MANAGER:
            return User.objects.filter(team=self.user.team)
        elif self.user.role == UserRole.SALES_REP:
            return [self.user]
        else:
            return User.objects.none()

    def _get_contacts(self):
        queryset = Contact.objects.filter(assigned_to__in=self.visible_users)

        return ContactFilter(
            self.request.GET,
            queryset=queryset,
        ).qs


class ContactAnalyticsService(AnalyticsService):
    def __init__(self, request, contacts=None):
        if contacts is not None:
            self.contacts = contacts
        else:
            super().__init__(request)

    def get_new_from_week(self):
        return self.contacts.filter(created_at__gte=timezone.now() - relativedelta(weeks=1)).count()

    def get_new_from_month(self):
        return self.contacts.filter(created_at__gte=timezone.now() - relativedelta(months=1)).count()

    def get_total_by_contact_status(self):
        return self.contacts.values("status").annotate(
            count=Count("id"),
        )

    def get_total_by_lead_source(self):
        result = self.contacts.values("lead_source").annotate(
            count=Count("id"),
            won_deals=Count("id", filter=Q(deals__stage=PipelineStage.CLOSED_WON))
        )
        return result

    def get_data(self):
        result = dict()

        result["total"] = self.contacts.count()
        result["new_from_last_week"] = self.get_new_from_week()
        result["new_from_last_month"] = self.get_new_from_month()
        result["total_by_contact_status"] = self.get_total_by_contact_status()
        result["total_by_lead_source"] = self.get_total_by_lead_source()

        return result


class ContactByPipelineAnalyticsService(AnalyticsService):
    def __init__(self, request):
        super().__init__(request)
        self.pipelines = self._get_pipelines()

    def _get_pipelines(self):
        return Pipeline.objects.filter(assigned_to__in=self.visible_users)

    def get_data(self):
        result = []

        for pipeline in self.pipelines:
            pipeline_contacts = self.contacts.filter(deals__pipeline=pipeline)
            result.append({
                "pipeline_name": pipeline.name,
                "product": pipeline.product.name,
                "assigned_to": pipeline.assigned_to.email,
                "analytics": ContactAnalyticsService(request=self.request, contacts=pipeline_contacts).get_data(),
            })

        return result


class ContactByTeamsAnalyticsService:
    def __init__(self, request):
        self.request = request
        self.contacts = self._get_contacts()
        self.teams = Team.objects.all()

    def _get_contacts(self):
        # для фільтрації, якщо при запиті були використані фільтри

        return ContactFilter(
            self.request.GET,
            queryset=Contact.objects.all(),
        ).qs

    def get_data(self):
        result = []

        for team in self.teams:
            team_contacts = self.contacts.filter(assigned_to__team=team)

            # в команди може бути один менеджер, не бути жодного або бути декілька
            # тому враховуються всі випадки
            managers = []
            for manager in team.users.filter(role='manager'):
                managers.append(manager.email)
            result.append({
                "team_name": team.name,
                "managers": managers,
                "analytics": ContactAnalyticsService(request=self.request, contacts=team_contacts).get_data(),
            })

        return result
