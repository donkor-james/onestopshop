from django.core.mail import send_mail
from backend.config.settings import base
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='send_otp_code', max_retries=3, default_retry_delay=60)
def send_otp_code(self, user, otp):

    subject = "OneStopShop Email Verification"
    message = f"""
Hello, {user.first_name}\n
Welcome to OneStopShop!
Your OTP is {otp}.\n
It’s valid for 10 minutes. Enter this OTP to complete your account signup \n

The OneStopShop Team.
"""
    try:
        send_mail(subject=subject, message=message, from_email=base.EMAIL_HOST_USER,
                  recipient_list=[user.email], fail_silently=False)
        logger.info(f"OTP email sent to {user.email} with OTP: {otp}")
    except Exception as e:
        logger.error(f"Failed to send OTP email to {user.email}: {e}")
