from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from .models import Notification


@shared_task
def check_scheduled_activities():
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
