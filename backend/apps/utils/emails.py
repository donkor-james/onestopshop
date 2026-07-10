import secrets
from django.core.mail import send_mail
from backend.config.settings import base


def send_verification_code(user):
    otp = ''.join(str(secrets.randbelow(10)) for _ in range(6))

    subject = "OneStopShop Email Verification"
    message = f"""
Hello, {user.first_name}\n
Welcome to OneStopShop!
Your OTP is {otp}.\n
It’s valid for 10 minutes. Enter this OTP to complete your account signup \n

The OneStopShop Team.
"""

    send_mail(subject=subject, message=message, from_email=base.EMAIL_HOST_USER,
              recipient_list=[user.email], fail_silently=False)
