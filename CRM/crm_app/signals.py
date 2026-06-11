from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Deal, DealStageHistory


@receiver(pre_save, sender=Deal)
def log_stage_change(sender, instance, **kwargs):
    if not instance.pk:  # новий об'єкт — пропускаємо
        return

    try:
        old_deal = Deal.objects.get(pk=instance.pk)
    except Deal.DoesNotExist:
        return

    if old_deal.stage != instance.stage:  # stage змінився
        DealStageHistory.objects.create(
            deal=instance,
            old_stage=old_deal.stage,
            new_stage=instance.stage,
            changed_by=instance._changed_by,  # юзер з view
        )
