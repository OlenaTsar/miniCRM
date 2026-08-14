from django.db.models.signals import pre_delete
from django.dispatch import receiver

from crm_app.tasks import create_archiving
from crm_app.models import Deal, Pipeline, Activity, ArchivingType
from auth_app.models import User, Team


@receiver(pre_delete, sender=User)
def archive_on_user_delete(sender, instance, **kwargs):
    # архівація усіх pipelines, deals, activities, що відносяться до видаленого User
    pipeline_ids = list(instance.pipelines.values_list("id", flat=True))
    deal_ids = list(instance.deals.values_list("id", flat=True))
    activity_ids = list(instance.activities.values_list("id", flat=True))

    create_archiving.delay(
        archiving_type=ArchivingType.USER_DELETED,
        pipeline_ids=[str(i) for i in pipeline_ids],
        deal_ids=[str(i) for i in deal_ids],
        activity_ids=[str(i) for i in activity_ids],
        message=False,
    )


@receiver(pre_delete, sender=Team)
def archive_on_team_delete(sender, instance, **kwargs):
    pipeline_ids = list(Pipeline.objects.filter(
        assigned_to__team=instance
    ).values_list("id", flat=True))
    deal_ids = list(Deal.objects.filter(
        assigned_to__team=instance
    ).values_list("id", flat=True))
    activity_ids = list(Activity.objects.filter(
        assigned_to__team=instance
    ).values_list("id", flat=True))

    create_archiving.delay(
        archiving_type=ArchivingType.TEAM_DELETED,
        pipeline_ids=[str(i) for i in pipeline_ids],
        deal_ids=[str(i) for i in deal_ids],
        activity_ids=[str(i) for i in activity_ids],
    )
