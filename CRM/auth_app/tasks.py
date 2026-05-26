from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def send_verification_email(user_email, token):
    link = f"{settings.FRONTEND_URL}/api/auth/verify-email/{token}/"
    send_mail(
        subject="Confirm your email",
        message=f"Click the link to activate your account:\n{link}",
        from_email="noreply@minicrm.com",
        recipient_list=[user_email],
    )
