import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CRM.settings")

app = Celery("CRM")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()  # автоматично знаходить tasks.py у всіх app

# django-celery-beat
# автоматично перевіряє чи потрібно відправити сповіщення
app.conf.beat_schedule = {
    "check_scheduled_activities-every-minute": {
        "task": "crm_app.tasks.check_scheduled_activities",
        "schedule": crontab(minute="*/1"),  # кожну хвилину
    },
}

# автоматична архівація першого числа кожного місяця угод та їх активностей,
# які були завершені станом на перше число попереднього місяця.
app.conf.beat_schedule = {
    "monthly_archive_completed_deals_and_activities": {
        "task": "crm_app.tasks.monthly_archive_completed_deals_and_activities",
        "schedule": crontab(day_of_month="1", hour="0", minute="0")
    },
}
