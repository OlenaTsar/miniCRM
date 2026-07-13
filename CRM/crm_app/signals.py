import uuid
from datetime import timedelta
from django.utils import timezone

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Deal, DealStageHistory, Activity, ActivityLog, Notification, Pipeline
from .serializers import ActivitySerializer


@receiver(pre_save, sender=Pipeline)
def pipeline_change(sender, instance, **kwargs):
    if not instance.pk:  # новий об'єкт - пропускаємо
        return

    try:
        old_pipeline = Pipeline.objects.get(pk=instance.pk)  # старі дані з БД
    except Pipeline.DoesNotExist:
        return

    # якщо змінено assigned_to - змінюємо його в Deals (в Activities зміниться автоматично), які належать цій pipeline
    if old_pipeline.assigned_to != instance.assigned_to:
        for deal in instance.deals.all():
            deal.assigned_to = instance.assigned_to
            deal._changed_by = instance._changed_by
            deal.save()


@receiver(pre_save, sender=Deal)
def deal_change(sender, instance, **kwargs):
    if not instance.pk:  # новий об'єкт - пропускаємо
        return

    try:
        old_deal = Deal.objects.get(pk=instance.pk)  # старі дані з БД
    except Deal.DoesNotExist:
        return

    # якщо змінено assigned_to - змінюємо його в Activities, які належать цій deal
    if old_deal.assigned_to != instance.assigned_to:
        for activity in instance.activities.all():
            activity.assigned_to = instance.assigned_to
            activity._changed_by = instance._changed_by
            activity.save()

    # якщо було змінено assigned_to тільки угоди, без зміни усієї pipeline
    # переносимо угоду в pipeline нового користувача, що відповідає за той самий product
    if old_deal.assigned_to != instance.assigned_to and instance.pipeline.assigned_to != instance.assigned_to:
        instance.pipeline = instance.assigned_to.pipelines.filter(product=instance.product).first()


@receiver(pre_save, sender=Deal)
def log_stage_change(sender, instance, **kwargs):
    if not instance.pk:  # новий об'єкт - пропускаємо
        return

    try:
        old_deal = Deal.objects.get(pk=instance.pk)  # старі дані з БД
    except Deal.DoesNotExist:
        return

    if old_deal.stage != instance.stage:  # stage змінився
        DealStageHistory.objects.create(
            deal=instance,
            old_stage=old_deal.stage,
            new_stage=instance.stage,
            changed_by=instance._changed_by,  # юзер з view
        )


@receiver(post_save, sender=Activity)
def log_activity_create(sender, instance, created, **kwargs):
    # при створенні Activity
    if not created:  # тільки для нових об'єктів
        return

    # логування

    new_data = ActivitySerializer(instance).data

    # щоб зберегти UUID в JSON
    for key, value in new_data.items():
        if isinstance(value, uuid.UUID):
            new_data[key] = str(value)

    ActivityLog.objects.create(
        activity=instance,
        performed_by=instance._changed_by,
        action=ActivityLog.Action.CREATED,
        new_data=dict(new_data),  # конвертуємо в dict, щоб зберегти в форматі JSON
    )


@receiver(pre_save, sender=Activity)
def log_activity_change(sender, instance, **kwargs):
    if not instance.pk:  # новий об'єкт
        return

    try:
        old_activity = Activity.objects.get(pk=instance.pk)
    except Activity.DoesNotExist:
        return

    old_data = ActivitySerializer(old_activity).data
    new_data = ActivitySerializer(instance).data

    # щоб зберегти UUID в JSON
    for key, value in old_data.items():
        if isinstance(value, uuid.UUID):
            old_data[key] = str(value)
    for key, value in new_data.items():
        if isinstance(value, uuid.UUID):
            new_data[key] = str(value)

    if instance.completed_at:
        action = ActivityLog.Action.COMPLETED
    else:
        action = ActivityLog.Action.UPDATED

    ActivityLog.objects.create(
        activity=instance,
        performed_by=instance._changed_by,
        action=action,
        old_data=dict(old_data),  # конвертуємо в dict, щоб зберегти в форматі JSON
        new_data=dict(new_data),
    )


@receiver(post_save, sender=Activity)
def notification_create_update(sender, instance, created, **kwargs):
    # видалення Notification для завершеної Activity
    if instance.completed_at:
        Notification.objects.filter(activity=instance).delete()
        return

    now = timezone.now()
    if instance.due_date <= now + timedelta(hours=1):
        notify_at = now + timedelta(minutes=1)
    else:
        notify_at = instance.due_date - timedelta(hours=1)

    # при створенні Activity
    if created:
        Notification.objects.create(
            notify_at=notify_at,
            recipient=instance.assigned_to,
            activity=instance
        )
        return

    # при редагуванні Activity
    notification = instance.notification

    updated = []

    # зміна recipient, якщо було змінено assigned_to в активності
    if notification.recipient != instance.assigned_to:
        notification.recipient = instance.assigned_to
        updated.append("recipient")

    if notification.notify_at != notify_at:  # тобто змінено due_date
        notification.notify_at = notify_at
        updated.append("notify_at")

        if notification.sent_at:
            notification.sent_at = None
            notification.read_at = None
            updated.extend(["sent_at", "read_at"])

    if updated:
        notification.save(update_fields=updated)
