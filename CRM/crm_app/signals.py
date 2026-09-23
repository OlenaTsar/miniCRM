import uuid
from datetime import timedelta
from django.utils import timezone

from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver

from .models import (
    Deal,
    DealStageHistory,
    DealStatus,
    Activity,
    ActivityLog,
    Notification,
    Pipeline,
    Archive,
    ArchivingType,
    Product,
)
from .serializers import ActivitySerializer
from .tasks import create_archiving


@receiver(pre_save, sender=Pipeline)
def pipeline_change_assignee(sender, instance, **kwargs):
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
            deal.save()


@receiver(pre_delete, sender=Archive)
def archive_deleted(sender, instance, **kwargs):
    for pipeline in instance.pipelines.all():
        pipeline.archived = None
        pipeline.save()
    for deal in instance.deals.all():
        deal.archived = None
        deal.save()
    for activity in instance.activities.all():
        activity.archived = None
        activity.save()


@receiver(pre_save, sender=Pipeline)
def pipeline_archived_unarchived(sender, instance, **kwargs):
    if not instance.pk:  # новий об'єкт - пропускаємо
        return

    try:
        old_pipeline = Pipeline.objects.get(pk=instance.pk)  # старі дані з БД
    except Pipeline.DoesNotExist:
        return

    if old_pipeline.archived != instance.archived and instance.archived is not None:
        # автоматична архівація Deals, які відносяться до заархівованого pipeline
        for deal in instance.deals.all():
            deal.archived = instance.archived
            deal.save()
    elif old_pipeline.archived != instance.archived and instance.archived is None:
        # автоматична деархівація Deals, які були в одній архівації з pipeline
        for deal in old_pipeline.archived.deals.filter(pipeline=old_pipeline):
            deal.archived = None
            deal.save()


@receiver(pre_save, sender=Deal)
def deal_archived_unarchived(sender, instance, **kwargs):
    if not instance.pk:  # новий об'єкт - пропускаємо
        return

    try:
        old_deal = Deal.objects.get(pk=instance.pk)  # старі дані з БД
    except Deal.DoesNotExist:
        return

    if old_deal.archived != instance.archived and instance.archived is not None:
        # автоматична архівація Activities, які відносяться до заархівованого Deal
        for activity in instance.activities.all():
            activity.archived = instance.archived
            activity.save()
    elif old_deal.archived != instance.archived and instance.archived is None:
        # автоматична деархівація Activities, які були в одній архівації з Deal
        for activity in old_deal.archived.activities.filter(deal=old_deal):
            activity.archived = None
            activity.save()


@receiver(pre_save, sender=Activity)
def activity_archived_unarchived(sender, instance, **kwargs):
    if not instance.pk:  # новий об'єкт - пропускаємо
        return

    try:
        old_activity = Activity.objects.get(pk=instance.pk)  # старі дані з БД
    except Activity.DoesNotExist:
        return

    now = timezone.now()

    if old_activity.archived != instance.archived and instance.archived is not None:
        # видалення Notification при архівації Activity
        Notification.objects.filter(activity=instance).delete()
    elif (old_activity.archived != instance.archived
          and instance.archived is None
          and not instance.completed_at
          and instance.due_date > now + timedelta(minutes=1)):
        # створення нового Notification при деархівації Activity,
        # якщо активність не завершена і не є простроченою
        if instance.due_date <= now + timedelta(hours=1):
            notify_at = now + timedelta(minutes=1)
        else:
            notify_at = instance.due_date - timedelta(hours=1)

        Notification.objects.create(
            notify_at=notify_at,
            recipient=instance.assigned_to,
            activity=instance
        )


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
            activity._changed_by = getattr(instance, "_changed_by", None)
            activity.save()

    # якщо було змінено assigned_to тільки угоди, без зміни усієї pipeline
    # переносимо угоду в pipeline нового користувача, що відповідає за той самий product
    if old_deal.assigned_to != instance.assigned_to and instance.pipeline.assigned_to != instance.assigned_to:
        instance.pipeline = instance.assigned_to.pipelines.filter(product=instance.product).first()

    # якщо було змінено pipeline угоди, але assigned_to угоди не збігається з assigned_to нового pipeline
    # (при перенесені угоди в pipeline іншого користувача)
    # встановлюємо assigned_to такий, як в нового pipeline
    if old_deal.pipeline != instance.pipeline and instance.pipeline.assigned_to != instance.assigned_to:
        instance.assigned_to = instance.pipeline.assigned_to


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


@receiver(pre_save, sender=Deal)
def remove_activity_notification_for_closed_deal(sender, instance, **kwargs):
    if not instance.pk:  # новий об'єкт - пропускаємо
        return

    try:
        old_deal = Deal.objects.get(pk=instance.pk)  # старі дані з БД
    except Deal.DoesNotExist:
        return

    # видалення сповіщення для активності завершеної угоди, якщо сповіщення ще не було надіслано
    if old_deal.status != instance.status and instance.status == DealStatus.CLOSED:
        notifications = Notification.objects.filter(activity__in=instance.activities.all(), sent_at__isnull=True)
        for notification in notifications:
            notification.delete()


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

    performed_by = getattr(instance, "_changed_by", None)

    ActivityLog.objects.create(
        activity=instance,
        performed_by=performed_by,
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

    performed_by = getattr(instance, "_changed_by", None)

    ActivityLog.objects.create(
        activity=instance,
        performed_by=performed_by,
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
    if not Notification.objects.filter(activity=instance).exists():
        # у випадку, якщо сповіщення було видалене, наприклад, для архівованої активності
        return

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


@receiver(pre_delete, sender=Product)
def archive_on_product_delete(sender, instance, **kwargs):
    # архівація усіх Pipelines, Deals та Activities, що відносяться до видаленого Product
    pipelines = instance.pipelines.all()

    pipeline_ids = list(pipelines.values_list("id", flat=True))
    deal_ids = list(
        Deal.objects.filter(
            pipeline__in=pipelines
        ).values_list("id", flat=True)
    )
    activity_ids = list(
        Activity.objects.filter(
            deal_id__in=deal_ids
        ).values_list("id", flat=True)
    )

    create_archiving.delay(
        archiving_type=ArchivingType.PRODUCT_DELETED,
        pipeline_ids=[str(i) for i in pipeline_ids],
        deal_ids=[str(i) for i in deal_ids],
        activity_ids=[str(i) for i in activity_ids],
    )
