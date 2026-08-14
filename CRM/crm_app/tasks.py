from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q

from .models import Notification, Archive, Pipeline, Deal, Activity, ArchivingType
from auth_app.models import User


@shared_task
def check_scheduled_activities():
    # шукає сповіщення, час відправки якого настав і яке не було відправлене
    # надсилає сповіщення
    now = timezone.now()
    notifications = Notification.objects.filter(
        notify_at__lt=now,
        sent_at__isnull=True,
    )
    for notification in notifications:
        send_scheduled_notification.delay(str(notification.id))
        notification.sent_at = now
        notification.save(update_fields=['sent_at'])


@shared_task
def send_scheduled_notification(notification_id):
    # відправляє повідомлення про заплановану активність
    notification = Notification.objects.get(id=notification_id)
    activity = notification.activity

    due_date = str(activity.due_date)[:16]
    activity_type = activity.get_activity_type_display()
    link = f"{settings.FRONTEND_URL}/api/activities/{activity.id}/"

    send_mail(
        subject=f"Scheduled activity {activity_type}",
        message=f"{activity_type} '{activity.title}'. Due date: {due_date}\nLink: {link}",
        from_email="noreply@minicrm.com",
        recipient_list=[notification.recipient.email],
    )


@shared_task
def send_data_archiving_notification(user_id, archive_id):
    # відправляє повідомлення про архівацію
    send_to = User.objects.get(id=user_id)
    archive = Archive.objects.get(id=archive_id)

    pipelines = archive.pipelines.filter(assigned_to=send_to)
    deals = archive.deals.filter(assigned_to=send_to)
    activities = archive.activities.filter(assigned_to=send_to)

    message = f"Archiving Type: {archive.archiving_type}\n"

    if pipelines.exists():
        count = pipelines.count()
        message += f"\nYour {count} {"pipeline" if count == 1 else "pipelines"} have been archived.\n"
        message += "Pipeline: " if count == 1 else "Pipelines:\n"
        for pipeline in pipelines:
            message += "\t" + pipeline.name + '\n'
    if deals.exists():
        count = deals.count()
        message += f"\nYour {count} {"deal" if count == 1 else "deals"} have been archived.\n"
        message += "Deal: " if count == 1 else "Deals:\n"
        for deal in deals:
            message += "\t" + deal.name + '\n'
    if activities.exists():
        count = activities.count()
        message += f"\nYour {count} {"activity" if count == 1 else "activities"} have been archived.\n"
        message += "Activity: " if count == 1 else "Activities:\n"
        for activity in activities:
            message += "\t" + activity.title + '\n'

    send_mail(
        subject=f"Data Archiving Notification",
        message=message,
        from_email="noreply@minicrm.com",
        recipient_list=[send_to.email],
    )


@shared_task
def create_archiving(archiving_type, pipeline_ids=None, deal_ids=None, activity_ids=None, message=True):
    # створює архівацію і додає до неї pipelines, deals, activities

    archive = Archive.objects.create(archiving_type=archiving_type)

    if pipeline_ids is not None:
        Pipeline.objects.filter(id__in=pipeline_ids, archived__isnull=True).update(archived=archive)
    if deal_ids is not None:
        Deal.objects.filter(id__in=deal_ids, archived__isnull=True).update(archived=archive)
    if activity_ids is not None:
        # оновлюємо через save, а не через update, щоб спрацював signal для видалення Notifications
        activities = Activity.objects.filter(id__in=activity_ids, archived__isnull=True)

        for activity in activities:
            activity.archived = archive
            activity.save()

    if message:
        users = User.objects.filter(
            Q(pipelines__archived=archive) |
            Q(deals__archived=archive) |
            Q(activities__archived=archive)
        ).distinct()

        for user in users:
            send_data_archiving_notification.delay(str(user.id), str(archive.id))


@shared_task
def monthly_archive_completed_deals_and_activities():
    # першого числа кожного місяця автоматично архівуються угоди та їх активності,
    # які були завершені станом на перше число попереднього місяця.
    now = timezone.now()
    previous_month_start = (now - timedelta(days=1)).replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    deals = Deal.objects.filter(
        closed_at__lt=previous_month_start,
        archived__isnull=True,
    )

    deal_ids = list(deals.values_list("id", flat=True))
    activity_ids = list(deals.activities.values_list("id", flat=True))

    create_archiving.delay(
        archiving_type=ArchivingType.PERIODIC,
        deal_ids=[str(i) for i in deal_ids],
        activity_ids=[str(i) for i in activity_ids],
    )
